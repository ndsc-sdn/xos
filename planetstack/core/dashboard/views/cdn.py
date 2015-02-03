from view_common import *
from planetstack_analytics import DoPlanetStackAnalytics, PlanetStackAnalytics, RED_LOAD, BLUE_LOAD

def getCDNContentProviderData():
    cps = []
    for dm_cp in ContentProvider.objects.all():
        cp = {"name": dm_cp.name,
              "account": dm_cp.account}
        cps.append(cp)

    return cps

def getCDNOperatorData(randomizeData = False, wait=True):
    HPC_SLICE_NAME = "HyperCache"

    bq = PlanetStackAnalytics()

    rows = bq.get_cached_query_results(bq.compose_cached_query(), wait)

    # wait=False on the first time the Dashboard is opened. This means we might
    # not have any rows yet. The dashboard code polls every 30 seconds, so it
    # will eventually pick them up.

    if rows:
        rows = bq.postprocess_results(rows, filter={"event": "hpc_heartbeat"}, maxi=["cpu"], count=["hostname"], computed=["bytes_sent/elapsed"], groupBy=["Time","site"], maxDeltaTime=80)

        # dictionaryize the statistics rows by site name
        stats_rows = {}
        for row in rows:
            stats_rows[row["site"]] = row
    else:
        stats_rows = {}

    slice = Slice.objects.filter(name=HPC_SLICE_NAME)
    if slice:
        slice_slivers = list(slice[0].slivers.all())
    else:
        slice_slivers = []

    new_rows = {}
    for site in Site.objects.all():
        # compute number of slivers allocated in the data model
        allocated_slivers = 0
        for sliver in slice_slivers:
            if sliver.node.site == site:
                allocated_slivers = allocated_slivers + 1

        stats_row = stats_rows.get(site.name,{})

        max_cpu = stats_row.get("max_avg_cpu", stats_row.get("max_cpu",0))
        cpu=float(max_cpu)/100.0
        hotness = max(0.0, ((cpu*RED_LOAD) - BLUE_LOAD)/(RED_LOAD-BLUE_LOAD))

        try:
           lat=float(site.location.latitude)
           long=float(site.location.longitude)
        except:
           lat=0
           long=0

        # format it to what that CDN Operations View is expecting
        new_row = {"lat": lat,
               "long": long,
               "health": 0,
               #"numNodes": int(site.nodes.count()),
               "activeHPCSlivers": int(stats_row.get("count_hostname", 0)),     # measured number of slivers, from bigquery statistics
               "numHPCSlivers": allocated_slivers,                              # allocated number of slivers, from data model
               "siteUrl": str(site.site_url),
               "bandwidth": stats_row.get("sum_computed_bytes_sent_div_elapsed",0),
               "load": max_cpu,
               "hot": float(hotness)}
        new_rows[str(site.name)] = new_row

    # get rid of sites with 0 slivers that overlap other sites with >0 slivers
    for (k,v) in new_rows.items():
        bad=False
        if v["numHPCSlivers"]==0:
            for v2 in new_rows.values():
                if (v!=v2) and (v2["numHPCSlivers"]>=0):
                    d = haversine(v["lat"],v["long"],v2["lat"],v2["long"])
                    if d<100:
                         bad=True
            if bad:
                del new_rows[k]

    return new_rows

class DashboardSummaryAjaxView(View):
    def get(self, request, **kwargs):
        def avg(x):
            if len(x)==0:
                return 0
            return float(sum(x))/len(x)

        sites = getCDNOperatorData().values()

        sites = [site for site in sites if site["numHPCSlivers"]>0]

        total_slivers = sum( [site["numHPCSlivers"] for site in sites] )
        total_bandwidth = sum( [site["bandwidth"] for site in sites] )
        average_cpu = int(avg( [site["load"] for site in sites] ))

        result= {"total_slivers": total_slivers,
                "total_bandwidth": total_bandwidth,
                "average_cpu": average_cpu}

        return HttpResponse(json.dumps(result), content_type='application/javascript')

class DashboardAddOrRemoveSliverView(View):
    # TODO: deprecate this view in favor of using TenantAddOrRemoveSliverView

    def post(self, request, *args, **kwargs):
        siteName = request.POST.get("site", None)
        actionToDo = request.POST.get("actionToDo", "0")

        siteList = [Site.objects.get(name=siteName)]
        slice = Slice.objects.get(name="HyperCache")

        if request.user.isReadOnlyUser():
            return HttpResponseForbidden("User is in read-only mode")

        if (actionToDo == "add"):
            user_ip = request.GET.get("ip", get_ip(request))
            slice_increase_slivers(request.user, user_ip, siteList, slice, image.objects.all()[0], 1)
        elif (actionToDo == "rem"):
            slice_decrease_slivers(request.user, siteList, slice, 1)

        print '*' * 50
        print 'Ask for site: ' + siteName + ' to ' + actionToDo + ' another HPC Sliver'
        return HttpResponse(json.dumps("Success"), content_type='application/javascript')

class DashboardAjaxView(View):
    def get(self, request, **kwargs):
        return HttpResponse(json.dumps(getCDNOperatorData(True)), content_type='application/javascript')
