'use strict';

angular.module('xos.vpnDashboard', [
  'ngResource',
  'ngCookies',
  'ngLodash',
  'ui.router',
  'xos.helpers'
])
.config(($stateProvider) => {
  $stateProvider
  .state('vpn-list', {
    url: '/',
    template: '<vpn-list></vpn-list>'
  })
  .state('cleint-script', {
    url: '/client/:pk',
    template: '<client-script></client-script>'
  });
})
.service('Vpn', function($http, $q){

  this.getVpnTenants = () => {
    let deferred = $q.defer();

    $http.get('/xoslib/vpntenants/')
    .then((res) => {
      deferred.resolve(res.data)
    })
    .catch((e) => {
      deferred.reject(e);
    });

    return deferred.promise;
  }
  this.getVpnTenants = (pk) => {
    let deferred = $q.defer();

    $http.get('/xoslib/clientscript/', {params: {pk: pk}})
    .then((res) => {
      deferred.resolve(res.data)
    })
    .catch((e) => {
      deferred.reject(e);
    });

    return deferred.promise;
  };
})
.config(function($httpProvider){
  $httpProvider.interceptors.push('NoHyperlinks');
})
.directive('vpnList', function(){
  return {
    restrict: 'E',
    scope: {},
    bindToController: true,
    controllerAs: 'vm',
    templateUrl: 'templates/vpn-list.tpl.html',
    controller: function(Vpn){
      // retrieving user list
      Vpn.getVpnTenants()
      .then((vpns) => {
        this.vpns = vpns;
      })
      .catch((e) => {
        throw new Error(e);
      });
    }
  };
})
.directive('clientScript', function(){
  return {
    restrict: 'E',
    scope: {
      pk: '=pk',
    },
    bindToController: true,
    controllerAs: 'vm',
    templateUrl: 'templates/client-script.tpl.html',
    controller: function(Vpn){
      // retrieving user list
      Vpn.getClientScript(pk)
      .then((script_location) => {
        this.script_location = script_location;
      })
      .catch((e) => {
        throw new Error(e);
      });
    }
  };
});
