# Istio "Hello World" my way

## What is this repo?

This is a really simple application I wrote over holidays a year ago (12/17) that details my experiences and
feedback with istio.  To be clear, its a really basic NodeJS application that i used here but more importantly, it covers
the main sections of [Istio](https://istio.io/) that i was seeking to understand better (if even just as a helloworld).  

I do know isito has the "[bookinfo](https://github.com/istio/istio/tree/master/samples/bookinfo)" application but the best way
i understand something is to rewrite sections and only those sections from the ground up.

## Istio version used

* 04/28/20: Istio 1.5.2
* 10/12/19: Istio 1.3.2
* 03/10/19:  Istio 1.1.0
* 01/09/19:  Istio 1.0.5
* [Prior Istio Versions](https://github.com/salrashid123/istio_helloworld/tags)


## What i tested

- [Basic istio Installation on Google Kubernetes Engine](#lets-get-started)
- [Grafana, Prometheus, Kiali, Jaeger](#setup-some-tunnels-to-each-of-the-services)
- [Route Control](#route-control)
- [Canary Deployments with VirtualService](#canary-deployments-with-virtualservice)
- [Destination Rules](#destination-rules)
- [Egress Rules](#egress-rules)
- [Egress Gateway](#egress-gateway)
- [WebAssembly](#webassembly)
- [LUA HttpFilter](#lua-httpfilter)
- [Authorization](#autorization)
- [JWT Authentication an Authorization](#jwt-auth-autorization)
- [Service to Service Authentication Policy](service-to-service-rbac-and-authentication-policy)
- [Internal LoadBalancer (GCP)](#internal-loadbalancer)
- [Mixer Out of Process Authorization Adapter](https://github.com/salrashid123/istio_custom_auth_adapter)
- [Access GCE MetadataServer](#access-GCE-metadataServer)

You can also find info about istio+external authorization server here:

- [Istio External Authorization Server](https://github.com/salrashid123/istio_external_authorization_server)


## What is the app you used?

NodeJS in a Dockerfile...something really minimal.  You can find the entire source under the 'nodeapp' folder in this repo.

The endpoints on this app are as such:

- ```/```:  Does nothing;  ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L24))
- ```/varz```:  Returns all the environment variables on the current Pod ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L33))
- ```/version```: Returns just the "process.env.VER" variable that was set on the Deployment ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L37))
- ```/backend```: Return the nodename, pod name.  Designed to only get called as if the applciation running is a `backend` ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L41))
- ```/hostz```:  Does a DNS SRV lookup for the `backend` and makes an http call to its `/backend`, endpoint ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L45))
- ```/requestz```:  Makes an HTTP fetch for several external URLs (used to show egress rules) ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L120))
- ```/headerz```:  Displays inbound headers
 ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L115))
- ```/metadata```: Access the GCP MetadataServer using hostname and link-local IP address ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L125))
- ```/remote```: Access `/backend` while deployed in a remote istio cluster  ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L145))

I build and uploaded this app to dockerhub at

```
docker.io/salrashid123/istioinit:1
docker.io/salrashid123/istioinit:2
```

(basically, they're both the same application but each has an environment variable that signifies which 'verison; they represent.  The version information for each image is returned by the `/version` endpoint)

You're also free to build and push these images directly:
```
docker build  --build-arg VER=1 -t your_dockerhub_id/istioinit:1 .
docker build  --build-arg VER=2 -t your_dockerhub_id/istioinit:2 .

docker push your_dockerhub_id/istioinit:1
docker push your_dockerhub_id/istioinit:2
```

To give you a sense of the differences between a regular GKE specification yaml vs. one modified for istio, you can compare:
- [all-istio.yaml](all-istio.yaml)  vs [all-gke.yaml](all-gke.yaml)
(review Ingress config, etc)

## Lets get started

### Create a 1.1+ GKE Cluster and Bootstrap Istio

Note, the following cluster is setup with a  [aliasIPs](https://cloud.google.com/kubernetes-engine/docs/how-to/alias-ips) (`--enable-ip-alias` )

We will be installing istio with [istioctl](https://istio.io/docs/setup/install/istioctl/)

```bash
gcloud container  clusters create cluster-1 --machine-type "n1-standard-2" --zone us-central1-a  --num-nodes 4 --enable-ip-alias -q

gcloud container clusters get-credentials cluster-1 --zone us-central1-a

kubectl create clusterrolebinding cluster-admin-binding --clusterrole=cluster-admin --user=$(gcloud config get-value core/account)

kubectl create ns istio-system

export ISTIO_VERSION=1.5.2

 wget https://github.com/istio/istio/releases/download/$ISTIO_VERSION/istio-$ISTIO_VERSION-linux.tar.gz 
 tar xvf istio-$ISTIO_VERSION-linux.tar.gz 
 rm istio-$ISTIO_VERSION-linux.tar.gz 

 wget https://github.com/istio/istio/releases/download/$ISTIO_VERSION/istioctl-$ISTIO_VERSION-linux.tar.gz
  tar xvf istioctl-$ISTIO_VERSION-linux.tar.gz
 rm istioctl-$ISTIO_VERSION-linux.tar.gz

 wget https://storage.googleapis.com/kubernetes-helm/helm-v2.11.0-linux-amd64.tar.gz
 tar xf helm-v2.11.0-linux-amd64.tar.gz
 rm helm-v2.11.0-linux-amd64.tar.gz

 export PATH=`pwd`:`pwd`/linux-amd64/:$PATH

cd istio-$ISTIO_VERSION

istioctl manifest apply --set profile=demo   \
 --set values.global.controlPlaneSecurityEnabled=true  \
 --set values.global.mtls.enabled=true  \
 --set values.sidecarInjectorWebhook.enabled=true  \
 --set values.gateways.istio-egressgateway.enabled=true -f ../overlay-istio-gateway.yaml

## https://github.com/istio/istio/pull/22951
## once that is fixed, use  --set meshConfig.outboundTrafficPolicy.mode=REGISTRY_ONLY  
## in the command above, for now apply manual egress policy 
kubectl get configmap istio -n istio-system -o yaml | sed 's/mode: ALLOW_ANY/mode: REGISTRY_ONLY/g' | kubectl replace -n istio-system -f -

$ istioctl profile dump --config-path components.ingressGateways demo
$ istioctl profile dump --config-path values.gateways.istio-ingressgateway demo


kubectl label namespace default istio-injection=enabled
```

Wait maybe 2 to 3 minutes and make sure all the Deployments are live:

- For reference, here are the Istio [operator installation options](https://istio.io/docs/reference/config/istio.operator.v1alpha1/)

### Make sure the Istio installation is ready

Verify this step by making sure all the ```Deployments``` are Available.

```bash
$ kubectl get no,po,rc,svc,ing,deployment -n istio-system
NAME                                            STATUS   ROLES    AGE     VERSION
node/gke-cluster-1-default-pool-59e1c366-26wn   Ready    <none>   4m13s   v1.14.10-gke.27
node/gke-cluster-1-default-pool-59e1c366-67nl   Ready    <none>   4m21s   v1.14.10-gke.27
node/gke-cluster-1-default-pool-59e1c366-f43v   Ready    <none>   4m13s   v1.14.10-gke.27
node/gke-cluster-1-default-pool-59e1c366-xgbn   Ready    <none>   4m13s   v1.14.10-gke.27

NAME                                        READY   STATUS    RESTARTS   AGE
pod/grafana-556b649566-ndzgv                1/1     Running   0          56s
pod/istio-egressgateway-645d78f8dd-8vn5l    1/1     Running   0          61s
pod/istio-ilbgateway-84c65cfccb-v7vh7       1/1     Running   0          60s
pod/istio-ingressgateway-746fbb966d-ckf8x   1/1     Running   0          60s
pod/istio-tracing-7cf5f46848-mmkbb          1/1     Running   0          56s
pod/istiod-8cc9bfd95-9rlw2                  1/1     Running   0          80s
pod/kiali-b4b5b4fb8-smbhv                   1/1     Running   0          56s
pod/prometheus-75f89f4df8-jmck8             2/2     Running   0          56s

NAME                                TYPE           CLUSTER-IP    EXTERNAL-IP   PORT(S)                                                    AGE
service/grafana                     ClusterIP      10.0.9.158    <none>        3000/TCP                                                   56s
service/istio-egressgateway         ClusterIP      10.0.15.222   <none>        80/TCP,443/TCP,15443/TCP                                   60s
service/istio-ilbgateway            LoadBalancer   10.0.2.129    10.128.0.78   443:32056/TCP                                              59s
service/istio-ingressgateway        LoadBalancer   10.0.9.26     <pending>     443:30386/TCP                                              59s
service/istio-pilot                 ClusterIP      10.0.0.84     <none>        15010/TCP,15011/TCP,15012/TCP,8080/TCP,15014/TCP,443/TCP   80s
service/istiod                      ClusterIP      10.0.0.106    <none>        15012/TCP,443/TCP                                          79s
service/jaeger-agent                ClusterIP      None          <none>        5775/UDP,6831/UDP,6832/UDP                                 56s
service/jaeger-collector            ClusterIP      10.0.11.102   <none>        14267/TCP,14268/TCP,14250/TCP                              55s
service/jaeger-collector-headless   ClusterIP      None          <none>        14250/TCP                                                  55s
service/jaeger-query                ClusterIP      10.0.3.160    <none>        16686/TCP                                                  55s
service/kiali                       ClusterIP      10.0.2.120    <none>        20001/TCP                                                  55s
service/prometheus                  ClusterIP      10.0.0.170    <none>        9090/TCP                                                   55s
service/tracing                     ClusterIP      10.0.13.130   <none>        80/TCP                                                     55s
service/zipkin                      ClusterIP      10.0.13.242   <none>        9411/TCP                                                   55s

NAME                                         READY   UP-TO-DATE   AVAILABLE   AGE
deployment.extensions/grafana                1/1     1            1           56s
deployment.extensions/istio-egressgateway    1/1     1            1           61s
deployment.extensions/istio-ilbgateway       1/1     1            1           60s
deployment.extensions/istio-ingressgateway   1/1     1            1           60s
deployment.extensions/istio-tracing          1/1     1            1           56s
deployment.extensions/istiod                 1/1     1            1           80s
deployment.extensions/kiali                  1/1     1            1           56s
deployment.extensions/prometheus             1/1     1            1           56s

```


### Make sure the Istio an IP for the ```LoadBalancer``` is assigned:

Run

```bash
$ kubectl get svc istio-ingressgateway -n istio-system

export GATEWAY_IP=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo $GATEWAY_IP
```


### Setup some tunnels to each of the services

Open up several new shell windows and type in one line into each:
```
kubectl -n istio-system port-forward $(kubectl -n istio-system get pod -l app=grafana -o jsonpath='{.items[0].metadata.name}') 3000:3000

kubectl port-forward -n istio-system $(kubectl get pod -n istio-system -l app=jaeger -o jsonpath='{.items[0].metadata.name}') 16686:16686

kubectl -n istio-system port-forward $(kubectl -n istio-system get pod -l app=kiali -o jsonpath='{.items[0].metadata.name}') 20001:20001
```

Open up a browser (4 tabs) and go to:
- Kiali http://localhost:20001/kiali (username: admin, password: admin)
- Grafana http://localhost:3000/dashboard/db/istio-mesh-dashboard
- Jaeger http://localhost:16686


### Deploy the sample application

The default ```all-istio.yaml``` runs:

- Ingress with SSL
- Deployments:
- - myapp-v1:  1 replica
- - myapp-v2:  1 replica
- - be-v1:  1 replicas
- - be-v2:  1 replicas

basically, a default frontend-backend scheme with one replicas for each `v1` and `v2` versions.

> Note: the default yaml pulls and run my dockerhub image- feel free to change this if you want.


```bash
cd ../
kubectl apply -f all-istio.yaml
kubectl apply -f istio-lb-certs.yaml
```

Now enable the ingress gateway for both external and internal loadbalancer traffic on _only_ port `:443`:

```bash
kubectl apply -f istio-ingress-gateway.yaml -f istio-ingress-ilbgateway.yaml 

kubectl apply -f istio-fev1-bev1.yaml
```

Wait until the deployments complete:

```bash
$ kubectl get po,deployments,svc,ing
NAME                            READY   STATUS    RESTARTS   AGE
pod/be-v1-7b758776dc-hdjsj      2/2     Running   0          47s
pod/be-v2-5b679f79d7-qbt94      2/2     Running   0          47s
pod/myapp-v1-5f4dc769fc-fvtsz   2/2     Running   0          48s
pod/myapp-v2-67c664b475-rz7wp   2/2     Running   0          47s

NAME                             READY   UP-TO-DATE   AVAILABLE   AGE
deployment.extensions/be-v1      1/1     1            1           47s
deployment.extensions/be-v2      1/1     1            1           47s
deployment.extensions/myapp-v1   1/1     1            1           48s
deployment.extensions/myapp-v2   1/1     1            1           48s

NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)    AGE
service/be           ClusterIP   10.0.9.89    <none>        8080/TCP   47s
service/kubernetes   ClusterIP   10.0.0.1     <none>        443/TCP    6m55s
service/myapp        ClusterIP   10.0.1.17    <none>        8080/TCP   48s
```

Notice that each pod has two containers:  one is from isto, the other is the applicaiton itself (this is because we have automatic sidecar injection enabled on the `default` namespace).

Also note that in ```all-istio.yaml``` we did not define an ```Ingress``` object though we've defined a TLS secret with a very specific metadata name: ```istio-ingressgateway-certs```.  That is a special name for a secret that is used by Istio to setup its own ingress gateway:


#### Ingress Gateway Secret in 1.0.0+

Note the ```istio-ingress-gateway``` secret specifies the Ingress cert to use (the specific metadata name is special and is **required**)

```yaml
apiVersion: v1
data:
  tls.crt: _redacted_
  tls.key: _redacted_
kind: Secret
metadata:
  name: istio-ingressgateway-certs
  namespace: istio-system
type: kubernetes.io/tls
```

Remember we've acquired the ```$GATEWAY_IP``` earlier:

```bash
export GATEWAY_IP=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo $GATEWAY_IP
```

### Send Traffic

This section shows basic user->frontend traffic and see the topology and telemetry in the Kiali and Grafana consoles:

#### Frontend only

So...lets send traffic with the ip to the ```/versions```  on the frontend

```bash
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version; sleep 1; done
```

you may need to restart the ingress pod if the certs they used didn't pickup
```bash
INGRESS_POD_NAME=$(kubectl get po -n istio-system | grep ingressgateway\- | awk '{print$1}'); echo ${INGRESS_POD_NAME};
kubectl delete po/$INGRESS_POD_NAME -n istio-system
```

You should see a sequence of 1's indicating the version of the frontend you just hit
```
111111111111111111111111111111111
```
(source: [/version](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L37) endpoint)

You should also see on kiali just traffic from ingress -> `fe:v1`

![alt text](images/kiali_fev1.png)

and in grafana:

![alt text](images/grafana_fev1.png)


#### Frontend and Backend

Now the next step in th exercise:

to send requests to ```user-->frontend--> backend```;  we'll use the  ```/hostz``` endpoint to do that.  Remember, the `/hostz` endpoint takes a frontend request, sends it to the backend which inturn echos back the podName the backend runs as.  The entire response is then returned to the user.  This is just a way to show the which backend host processed the requests.

(note i'm using  [jq](https://stedolan.github.io/jq/) utility to parse JSON)

```bash
for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; sleep 1; done
```

you should see output indicating traffic from the v1 backend verison: ```be-v1-*```.  Thats what we expect since our original rule sets defines only `fe:v1` and `be:v1` as valid targets.

```bash
$ for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; sleep 1; done

"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
```

Note both Kiali and Grafana shows both frontend and backend service telemetry and traffic to ```be:v1```

![alt text](images/kiali_fev1_bev1.png)


![alt text](images/grafana_fev1_bev1.png)

## Route Control

This section details how to selectively send traffic to specific service versions and control traffic routing.

### Selective Traffic

In this sequence,  we will setup a routecontrol to:

1. Send all traffic to ```myapp:v1```.  
2. traffic from ```myapp:v1``` can only go to ```be:v2```

Basically, this is a convoluted way to send traffic from `fe:v1`-> `be:v2` even if all services and versions are running.

The yaml on ```istio-fev1-bev2.yaml``` would direct inbound traffic for ```myapp:v1``` to go to ```be:v2``` based on the ```sourceLabels:```.  The snippet for this config is:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: be-virtualservice
spec:
  gateways:
  - mesh
  hosts:
  - be
  http:
  - match:
    - sourceLabels:
        app: myapp
        version: v1
    route:
    - destination:
        host: be
        subset: v2
      weight: 100
---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: be-destination
spec:
  host: be
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
    loadBalancer:
      simple: ROUND_ROBIN
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

So lets apply the config with kubectl:

```bash
kubectl replace -f istio-fev1-bev2.yaml
```

After sending traffic,  check which backend system was called by invoking ```/hostz``` endpoint on the frontend.

What the ```/hostz``` endpoint does is takes a users request to ```fe-*``` and targets any ```be-*``` that is valid.  Since we only have ```fe-v1``` instances running and the fact we setup a rule such that only traffic from `fe:v1` can go to `be:v2`, all the traffic outbound for ```be-*``` must terminate at a ```be-v2```:

```bash
$ for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; sleep 1; done

"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
```

and on the frontend version is always one.
```bash
for i in {1..100}; do curl -k https://$GATEWAY_IP/version; sleep 1; done
11111111111111111111111111111
```

Note the traffic to ```be-v1``` is 0 while there is a non-zero traffic to ```be-v2``` from ```fe-v1```:

![alt text](images/kiali_route_fev1_bev2.png)

![alt text](images/grafana_fev1_bev2.png)


If we now overlay rules that direct traffic allow interleaved  ```fe(v1|v2) -> be(v1|v2)``` we expect to see requests to both frontend v1 and backend
```
kubectl replace -f istio-fev1v2-bev1v2.yaml
```

then frontend is both v1 and v2:
```bash
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version;  sleep 1; done
111211112122211121212211122211
```

and backend is responses comes from both be-v1 and be-v2

```bash
$ for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; sleep 1; done

"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
```

![alt text](images/kiali_route_fev1v2_bev1v2.png)

![alt text](images/grafana_fev1v2_bev1v2.png)


### Route Path

Now lets setup a more selective route based on a specific path in the URI:

- The rule we're defining is: "_First_ route requests to myapp where `path=/version` to only go to the ```v1``` set"...if there is no match, fall back to the default routes where you send `20%` traffic to `v1` and `80%` traffic to `v2`


```yaml
---
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: myapp-virtualservice
spec:
  hosts:
  - "*"
  gateways:
  - my-gateway
  http:
  - match:
    - uri:
        exact: /version
    route:
    - destination:
        host: myapp
        subset: v1
  - route:
    - destination:
        host: myapp
        subset: v1
      weight: 20
    - destination:
        host: myapp
        subset: v2
      weight: 80
```


```bash
kubectl replace -f istio-route-version-fev1-bev1v2.yaml
```

So check all requests to `/version` are `fe:v1`
```
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version; sleep 1; done
1111111111111111111
```

You may have noted how the route to any other endpoint other than `/version` destination is weighted split and not delcared round robin (eg:)
```yaml
  - route:
    - destination:
        host: myapp
        subset: v1
      weight: 20
    - destination:
        host: myapp
        subset: v2
      weight: 80
```

Anyway, now lets edit rule to  and change the prefix match to ```/xversion``` so the match *doesn't apply*.   What we expect is a request to http://gateway_ip/version will go to v1 and v2 (since the path rule did not match and the split is the fallback rule.

```
kubectl replace -f istio-route-version-fev1-bev1v2.yaml
```
Observe the version of the frontend you're hitting:

```bash
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version; sleep 1; done
2121212222222222222221122212211222222222222222
```

What you're seeing is ```myapp-v1``` now getting about `20%` of the traffic while ```myapp-v2``` gets `80%` because the previous rule doens't match.

Undo that change `/xversion` --> `/version` and reapply to baseline:

```
kubectl replace -f istio-route-version-fev1-bev1v2.yaml
```

#### Canary Deployments with VirtualService

You can use this traffic distribuion mechanism to run canary deployments between released versions.  For example, a rule like the following will split the traffic between `v1|v2` at `80/20` which you can use to gradually roll traffic over to `v2` by applying new percentage weights.


```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: myapp-virtualservice
spec:
  hosts:
  - "*"
  gateways:
  - my-gateway
  http:
  - route:
    - destination:
        host: myapp
        subset: v1
      weight: 80
    - destination:
        host: myapp
        subset: v2
      weight: 20
```
### Destination Rules

Lets configure Destination rules such that all traffic from ```myapp-v1``` round-robins to both version of the backend.

First lets  force all gateway requests to go to ```v1``` only:

on ```istio-fev1-bev1v2.yaml```:


```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: myapp-virtualservice
spec:
  hosts:
  - "*"
  gateways:
  - my-gateway
  http:
  - route:
    - destination:
        host: myapp
        subset: v1
```


And where the backend trffic is split between ```be-v1``` and ```be-v2``` with a ```ROUND_ROBIN```

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: be-destination
spec:
  host: be
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
    loadBalancer:
      simple: ROUND_ROBIN
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

After you apply the rule,

```
kubectl replace -f istio-fev1-bev1v2.yaml
```

you'll see frontend request all going to ```fe-v1```

```bash
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version; sleep 1; done
11111111111111
```

with backend requests coming from _pretty much_ round robin

```bash
$ for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; sleep 1; done

"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
```

Now change the ```istio-fev1-bev1v2.yaml```  to ```RANDOM``` and see response is from v1 and v2 random:
```bash
$ for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; sleep 1; done

"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"
"pod: [be-v1-7b758776dc-hdjsj]    node: [gke-cluster-1-default-pool-59e1c366-26wn]"
"pod: [be-v2-5b679f79d7-qbt94]    node: [gke-cluster-1-default-pool-59e1c366-xgbn]"

```

### Internal LoadBalancer

The configuration here  sets up an internal loadbalancer on GCP to access an exposed istio service.

The config settings that enabled this during istio setup was done by an operator and annotation:

Specifically, we created a new `ingressGateway` and set its annotation to
`cloud.google.com/load-balancer-type: "internal"`


```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    ingressGateways:
      - name: istio-ingressgateway
        enabled: true
        k8s:
          service:
            ports:
            - name: https
              port: 443
              protocol: TCP
      - name: istio-ilbgateway
        enabled: true
        k8s:
          serviceAnnotations:
            cloud.google.com/load-balancer-type: "internal"
          service:
            ports:
            - port: 443
              name: https
              protocol: TCP
```

We did that duirng setup and later on, attached a Gateway to it which also exposed only `:443`

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway-ilb
spec:
  selector:
    istio: istio-ilbgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts:
    - "*"    
    tls:
      mode: SIMPLE
      serverCertificate: /etc/istio/ilbgateway-certs/tls.crt
      privateKey: /etc/istio/ilbgateway-certs/tls.key 
```


We also specified a `VirtualService` which selected these inbound gateways to the `myapp` service:  This configuration was defined when we applied `istio-fev1-bev1.yaml`:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: myapp-virtualservice
spec:
  hosts:
  - "*"
  gateways:
  - my-gateway
  - my-gateway-ilb  
  http:
  - route:
    - destination:
        host: myapp
        subset: v1
      weight: 100
```

Note the `gateways:` entry in the `VirtualService` includes `my-gateway-ilb` which is what defines `host:myapp, subset:v1` as a target for the ILB

```yaml
  gateways:
  - my-gateway
  - my-gateway-ilb
```

As mentioned above, we had to _manually_ specify the `port` the ILB will listen on for traffic inbound to this service. \

Finally, the certficates `Secret` mounted at `/etc/istio/ilbgateway-certs/` was specified this in the initial `all-istio.yaml` file:

```yaml
apiVersion: v1
data:
  tls.crt: LS0tLS1CR...
  tls.key: LS0tLS1CR...
kind: Secret
metadata:
  name: istio-ilbgateway-certs
  namespace: istio-system
type: kubernetes.io/tls
```

Now that the service is setup, acquire the ILB IP allocated

```bash
export ILB_GATEWAY_IP=$(kubectl -n istio-system get service istio-ilbgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo $ILB_GATEWAY_IP
```

![images/ilb.png](images/ilb.png)

Then from a GCE VM in the same VPC, send some traffic over on the internal address

```bash
you@gce-instance-1:~$ curl -vk https://10.128.0.78/

< HTTP/2 200 
< x-powered-by: Express
< content-type: text/html; charset=utf-8
< content-length: 19
< etag: W/"13-AQEDToUxEbBicITSJoQtsw"
< date: Fri, 22 Mar 2019 00:22:28 GMT
< x-envoy-upstream-service-time: 12
< server: istio-envoy
< 

Hello from Express!
```

- The Kiali console should show traffic from both gateways (if you recently sent traffic in externally and internally):

![images/ilb_traffic.png](images/ilb_traffic.png)

### Egress Rules

By default, istio blocks the cluster from making outbound requests.  There are several options to allow your service to connect externally:

* Egress Rules
* Egress Gateway
* Setting `global.proxy.includeIPRanges`

Egress rules prevent outbound calls from the server except with whiteliste addresses.

For example:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: ServiceEntry
metadata:
  name: bbc-ext
spec:
  hosts:
  - www.bbc.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
  resolution: DNS
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1alpha3
kind: ServiceEntry
metadata:
  name: google-ext
spec:
  hosts:
  - www.google.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  resolution: DNS
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: google-ext
spec:
  hosts:
  - www.google.com
  tls:
  - match:
    - port: 443
      sni_hosts:
      - www.google.com
    route:
    - destination:
        host: www.google.com
        port:
          number: 443
      weight: 100

```


Allows only ```http://www.bbc.com/*``` and ```https://www.google.com/*```

To test the default policies, the `/requestz` endpoint tries to fetch the following URLs:

```javascript
    var urls = [
                'https://www.google.com/robots.txt',
                'http://www.bbc.com/robots.txt',
                'http://www.google.com:443/robots.txt',
                'https://www.cornell.edu/robots.txt',
                'https://www.uwo.ca/robots.txt',
                'http://www.yahoo.com/robots.txt'
    ]
```

First make sure there is an inbound rule already running:

```bash
kubectl replace -f istio-fev1-bev1.yaml
```

And that you're using REGISTRY_ONLY:

```bash
kubectl get configmap istio -n istio-system -o yaml | grep -o "mode: REGISTRY_ONLY"
```

- Without egress rule, requests will fail:

```bash
curl -k -s  https://$GATEWAY_IP/requestz | jq  '.'
```

gives

```bash
[
  {
    "url": "https://www.google.com/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: Client network socket disconnected before secure TLS connection was established",
  },
  {
    "url": "http://www.google.com:443/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "http://www.bbc.com/robots.txt",
    "body": "",
    "statusCode": 502
  },
  {
    "url": "https://www.cornell.edu/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "https://www.uwo.ca/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: Client network socket disconnected before secure TLS connection was established",
  },
  {
    "url": "https://www.yahoo.com/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: Client network socket disconnected before secure TLS connection was established",
  },
  {
    "url": "http://www.yahoo.com:443/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
]

```

> Note: the `502` response for the ```bbc.com``` entry is the actual denial rule from the istio-proxy (`502`->Bad Gateway)


then apply the egress policy which allows ```www.bbc.com:80``` and ```www.google.com:443```

```
kubectl apply -f istio-egress-rule.yaml
```

gives

```bash
curl -s -k https://$GATEWAY_IP/requestz | jq  '.'
```

```bash
[
  {
    "url": "https://www.google.com/robots.txt",
    "statusCode": 200
  },
  {
    "url": "http://www.google.com:443/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "http://www.bbc.com/robots.txt",
    "statusCode": 200
  },
  {
    "url": "https://www.cornell.edu/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "https://www.uwo.ca/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "https://www.yahoo.com/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "http://www.yahoo.com:443/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
]

```

Notice that only one of the hosts worked over SSL worked

### Egress Gateway

THe egress rule above initiates the proxied connection from each sidecar....but why not initiate the SSL connection from a set of bastion/egress
gateways we already setup?   THis is where the [Egress Gateway](https://istio.io/docs/examples/advanced-egress/egress-gateway/) configurations come up but inorder to use this:  The following configuration will allow egress traffic for `www.yahoo.com` via the gateway.  See [HTTPS Egress Gateway](https://istio.io/docs/examples/advanced-gateways/egress-gateway/#egress-gateway-for-https-traffic)


So.. lets revert the config we setup above

```
kubectl delete -f istio-egress-rule.yaml
```

then lets apply the rule for the gateway:

```bash
kubectl apply -f istio-egress-gateway.yaml
```

Notice the gateway TLS mode is `PASSTHROUGH` ("_Note the PASSTHROUGH TLS mode which instructs the gateway to pass the ingress traffic AS IS, without terminating TLS._")
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: Gateway
metadata:
  name: istio-egressgateway
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: tls
      protocol: TLS
    hosts:
    - www.yahoo.com
    tls:
      mode: PASSTHROUGH
```

```bash
curl -s -k https://$GATEWAY_IP/requestz | jq  '.'
```

```bash
[
  {
    "url": "https://www.google.com/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "http://www.google.com:443/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "http://www.bbc.com/robots.txt",
    "body": "",
    "statusCode": 502
  },
  {
    "url": "https://www.cornell.edu/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "https://www.uwo.ca/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  },
  {
    "url": "https://www.yahoo.com/robots.txt",
    "statusCode": 200                  <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
  },
  {
    "url": "http://www.yahoo.com:443/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
    }
  }
]

```


You can also tail the egress gateway logs:

```bash
$  kubectl logs -f --tail=0  -l istio=egressgateway -n istio-system
[2020-04-29T15:23:39.949Z] "- - -" 0 - "-" "-" 829 5706 144 - "-" "-" "-" "-" "72.30.35.10:443" outbound|443||www.yahoo.com 10.12.1.4:57332 10.12.1.4:443 10.12.2.10:41592 www.yahoo.com -
[2020-04-29T15:23:48.195Z] "- - -" 0 - "-" "-" 829 5722 138 - "-" "-" "-" "-" "98.138.219.231:443" outbound|443||www.yahoo.com 10.12.1.4:40632 10.12.1.4:443 10.12.2.10:41658 www.yahoo.com -
```

### TLS Origination for Egress Traffic

In this mode, traffic exits the pod unencrypted but gets proxied via the gateway for an https destination.  For this to work, traffic must originate from the pod unencrypted but specify the port as an SSL port.  In current case, if you want to send traffic for `https://www.yahoo.com/robots.txt`, emit the request from the pod as `http://www.yahoo.com:443/robots.txt`.  Note the traffic is `http://` and the port is specified: `:443`


Ok, lets try it out, apply:

```
kubectl apply -f istio-egress-gateway-tls-origin.yaml
```

Then notice just the last, unencrypted traffic to yahoo succeeds

```
 curl -s -k https://$GATEWAY_IP/requestz | jq  '.
[
  {
    "url": "https://www.google.com/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: Client network socket disconnected before secure TLS connection was established",
    }
  },
  {
    "url": "http://www.google.com:443/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
    }
  },
  {
    "url": "http://www.bbc.com/robots.txt",
    "body": "",
    "statusCode": 502
  },
  {
    "url": "https://www.cornell.edu/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: Client network socket disconnected before secure TLS connection was established",
  },
  {
    "url": "https://www.uwo.ca/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: Client network socket disconnected before secure TLS connection was established",
    }
  },
  {
    "url": "http://www.yahoo.com/robots.txt",
    "statusCode": 200
  },
  {
    "url": "https://www.yahoo.com/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: Client network socket disconnected before secure TLS connection was established",
    }
  },
  {
    "url": "http://www.yahoo.com:443/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
    }
  }
]

```

### Bypass Envoy entirely

You can also configure the `global.proxy.includeIPRanges=` variable to completely bypass the IP ranges for certain serivces.   This setting is described under [Calling external services directly](https://istio.io/docs/tasks/traffic-management/egress/#calling-external-services-directly) and details the ranges that _should_ get covered by the proxy.  For GKE, you need to cover the subnets included and allocated:


### Access GCE MetadataServer

The `/metadata` endpoint access the GCE metadata server and returns the current projectID.  This endpoint makes three separate requests using the three formats I've see GCP client libraries use.  (note: the hostnames are supposed to resolve to the link local IP address shown below)

```javascript
app.get('/metadata', (request, response) => {

  var resp_promises = []
  var urls = [
              'http://metadata.google.internal/computeMetadata/v1/project/project-id',
              'http://metadata/computeMetadata/v1/project/project-id',
              'http://169.254.169.254/computeMetadata/v1/project/project-id'
  ]
```

So if you make an inital request, you'll see `404` errors from Envoy since we did not setup any rules.

```json
[
  {
    "url": "http://metadata.google.internal/computeMetadata/v1/project/project-id",
    "body": "",
    "statusCode": 502
  },
  {
    "url": "http://metadata/computeMetadata/v1/project/project-id",
    "body": "",
    "statusCode": 502
  },
  {
    "url": "http://169.254.169.254/computeMetadata/v1/project/project-id",
    "body": "",
    "statusCode": 502
  }
]
```

So lets do just that:

```
  kubectl apply -f istio-egress-rule-metadata.yaml
```

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: ServiceEntry
metadata:
  name: metadata-ext
spec:
  addresses: 
  - 169.254.169.254    
  hosts:
  - metadata.google.internal
  ports:
  - number: 80
    name: http
    protocol: HTTP
  resolution: STATIC
  location: MESH_EXTERNAL
  endpoints:
  - address: 169.254.169.254
```

Try it again and you should see 

```json
[
  {
    "url": "http://metadata.google.internal/computeMetadata/v1/project/project-id",
    "statusCode": 200
  },
  {
    "url": "http://metadata/computeMetadata/v1/project/project-id",
    "statusCode": 502
  },
  {
    "url": "http://169.254.169.254/computeMetadata/v1/project/project-id",
    "statusCode": 200
  }
]

```

### WebAssembly

Ref: [Redefining extensibility in proxies - introducing WebAssembly to Envoy and Istio](https://istio.io/blog/2020/wasm-announce/)

The following steps will deploy a trivial `wasm` module to the cluster that returns `hello world` back as a header.

We're using a pregenerated wasm module here but if you are interested in setting one up on your own, see

- [WebAssembly + Envoy Helloworld](https://gist.github.com/salrashid123/30fc1969b53c654310e25bca73bf5206)


Install `wasm` cli:

```bash
curl -sL https://run.solo.io/wasme/install | sh
export PATH=$HOME/.wasme/bin:$PATH
```

Create a simple 'helloworld' application

```bash
wasme init ./new-filter --language=assemblyscript --platform istio --disable-prompt

cd new-filter

[edit assembly/index.ts as necessary]

wasme build assemblyscript -t webassemblyhub.io/salrashid123/add-header:v0.1 .

wasme push webassemblyhub.io/salrashid123/add-header:v0.1

wasme pull webassemblyhub.io/salrashid123/add-header:v0.1 -v
```

Deploy to cluster via

`cli`:

```bash
# deploy
wasme deploy istio webassemblyhub.io/salrashid123/add-header:v0.1   \
    --id=myfilter    --namespace=default  \
      --config 'any'   --labels app=myapp

# remove
wasme undeploy istio webassemblyhub.io/salrashid123/add-header:v0.1   \
    --id=myfilter    --namespace=default  \
      --config 'any'   --labels app=myapp      
```

`crd`:

```bash
# install CRDs
kubectl apply -f https://github.com/solo-io/wasme/releases/latest/download/wasme.io_v1_crds.yaml
kubectl apply -f https://github.com/solo-io/wasme/releases/latest/download/wasme-default.yaml

# deploy
kubectl apply -f istio-fev1-wasm.yaml

# remove
kubectl delete -f istio-fev1-wasm.yaml
kubectl delete -f https://github.com/solo-io/wasme/releases/latest/download/wasme.io_v1_crds.yaml
kubectl delete -f https://github.com/solo-io/wasme/releases/latest/download/wasme-default.yaml
```

While its deployed, if you inoke an endpoint, you will see the custom header:

```bash
$ curl -vk  https://$GATEWAY_IP/headerz

< x-powered-by: Express
< content-type: application/json; charset=utf-8
< content-length: 610
< etag: W/"262-vyZHt8NIkso86UBB8CCgkNkdChw"
< date: Wed, 29 Apr 2020 15:57:39 GMT
< x-envoy-upstream-service-time: 35
< hello: world!                 <<<<<<<<<<<<<<<<
< server: istio-envoy
< 
```

### LUA HTTPFilter

The following will setup a simple Request/Response LUA `EnvoyFilter` for the frontent `myapp`:

The settings below injects headers in both the request and response streams:

```
kubectl apply -f istio-fev1-httpfilter-lua.yaml
```

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: http-lua
spec:
  workloadLabels:
    app: myapp
    version: v1
  filters:
  - listenerMatch:
      portNumber: 9080
      listenerType: SIDECAR_INBOUND
    filterName: envoy.lua
    filterType: HTTP
    filterConfig:
      inlineCode: |
        function envoy_on_request(request_handle)
          request_handle:headers():add("foo", "bar")
        end
        function envoy_on_response(response_handle)
          response_handle:headers():add("foo2", "bar2")
        end
```

Note the response headers back to the caller (`foo2:bar2`) and the echo of the headers as received by the service _from_ envoy (`foo:bar`)

```bash
$ curl -vk  https://$GATEWAY_IP/headerz 

> GET /headerz HTTP/2
> Host: 35.184.101.110
> User-Agent: curl/7.60.0
> Accept: */*

< HTTP/2 200 
< x-powered-by: Express
< content-type: application/json; charset=utf-8
< contLUAent-length: 626
< etag: W/"272-vkps3sJOT8NW67CxK6gzGw"
< date: Fri, 22 Mar 2019 00:40:36 GMT
< x-envoy-upstream-service-time: 7
< foo2: bar2
< server: istio-envoy

{
  "host": "35.184.101.110",
  "user-agent": "curl/7.60.0",
  "accept": "*/*",
  "x-forwarded-for": "10.128.15.224",
  "x-forwarded-proto": "https",
  "x-request-id": "5331b3a4-1a0c-4eaf-a7d0-5b33eb2b268d",
  "content-length": "0",
  "x-envoy-internal": "true",
  "x-forwarded-client-cert": "By=spiffe://cluster.local/ns/default/sa/myapp-sa;Hash=3ce2e36b58b41b777271f14234e4d930457754639d62df8c59b879bf7c47922a;Subject=\"\";URI=spiffe://cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account",
  "foo": "bar",                      <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
  "x-b3-traceid": "8c0c86470918440f1f24002aa1f402d1",
  "x-b3-spanid": "70db68a403e2d6a5",
  "x-b3-parentspanid": "1f24002aa1f402d1",
  "x-b3-sampled": "0"
}
```

You can also see the backend request header by running an echo back of those headers

```bash
curl -v -k https://$GATEWAY_IP/hostz

< HTTP/2 200 
< x-powered-by: Express
< content-type: application/json; charset=utf-8
< content-length: 168
< etag: W/"a8-+rQK5xf1qR07k9sBV9qawQ"
< date: Fri, 22 Mar 2019 00:44:30 GMT
< x-envoy-upstream-service-time: 33
< foo2: bar2   <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
< server: istio-envoy

```

### Authorization and Authorization

The following steps is basically another walkthrough of the [RequestAuthentication](https://istio.io/docs/reference/config/security/request_authentication/) and [AuthorizationPolicy](https://istio.io/docs/reference/config/security/authorization-policy/)


#### JWT Authentication and RBAC Authorization

In this section, we will extend the sample to implement JWT authentication from the client and also use claims within the JWT payload for an enhanced [Service Specific Policy](https://istio.io/docs/tasks/security/authn-policy/#service-specific-policy).

Specifically, this section will add perimeter [Authentication](https://istio.io/docs/concepts/security/#authentication) that validates a JWT token at ingress gateway and then RBAC policies at the Service level will further restrict requests.

There are two users: Alice, Bob and two services `svc1`, `svc2`. Alice should be allowed to access _only_ `svc1`, Bob should only access `svc2`.  Both users must present a JWT issued by the same issuer.  In this case, a Self Signed JWT certificate issued by Google.  You can also use Fireabase/Cloud Identity or any other JWT that provides a JWK URL)

This section involves several steps...first delete any configurations that may still be active.  We need to do this because we will create two _new_ services on the frontend `svc1`, `svc2`

```bash
kubectl delete -f istio-fev1-httpfilter-lua.yaml
kubectl delete -f istio-fev1-httpfilter-ext_authz.yaml 
kubectl delete -f istio-fev1-bev1v2.yaml	
kubectl delete -f all-istio.yaml


kubectl apply -f istio-lb-certs.yaml
kubectl apply -f istio-ingress-gateway.yaml
kubectl apply -f istio-ingress-ilbgateway.yaml 
```

You can verify the configuration that are active by running:

```bash
$ kubectl get svc,deployments,po,serviceaccounts,serviceentry,VirtualService,DestinationRule,ServiceRole,ServiceRoleBinding,RbacConfig,Secret,Policy,Gateway
```

Since the authentication mode described here involes a JWT, we will setup a Google Cloud Service Account the JWT provider.  You are ofcourse free to use any identity provide or even Firebase/[Cloud Identity](https://cloud.google.com/identity/docs/how-to/setup) 

First redeploy an application that has two frontend services `svc1`, `svc2` accessible using the `Host:` headervalues (`svc1.domain.com` and `svc2.domain.com`)

```
cd auth_rbac_policy/

kubectl apply -f auth-deployment.yaml -f istio-fe-svc1-fe-svc2.yaml
```

Check the application still works (it should; we didn't apply policies yet yet)

```bash
 curl -k -H "Host: svc1.example.com" -w "\n" https://$GATEWAY_IP/version
```


Apply the authentication policy that checks for a JWT signed by the service account and audience match on the service.  THe following policy will allow all three audience values through the ingress gateway but only those JWTs that match the audience for the service through at the service level:

To bootstrap all this, first we need some JWTS.  In this case, we will use GCP serice accounts
```
To bootstrap the sample client, go to the Google Cloud Console and download a service account JSON file as described [here](https://cloud.google.com/iam/docs/creating-managing-service-account-keys).  Copy the service account to the `auth_rbac_policy/jwt_cli` folder and save the JSON file as `svc_account.json`.

First get the name of the serice account that will sign the JWT:

```bash
cd auth_rbac_policy/jwt_cli/

export PROJECT_ID=`gcloud config get-value core/project`
gcloud iam service-accounts create sa-istio --display-name "JWT issuer for Istio helloworld"
export SA_EMAIL=sa-istio@$PROJECT_ID.iam.gserviceaccount.com
gcloud iam service-accounts keys create svc_account.json --iam-account=$SA_EMAIL
$ echo SA_EMAIL
```

Edit `auth-policy.yaml` file and replace the values where the service account email `$SA_EMAIL` is specified


After you apply the policy

```
kubectl apply -f auth-policy.yaml
```
Note that by default we have mTLS and deny by default

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
 name: deny-all-authz-ns
spec:
  {} 
---
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default-peerauth
  namespace: default
spec:
  mtls:
    mode: STRICT
```

make an api call with a malformed authentication header:

```bash
$  curl -k -H "Host: svc1.example.com" -H "Authorization: Bearer foo" -w "\n" https://$GATEWAY_IP/version
   Jwt is not in the form of Header.Payload.Signature
```

now try without a header entirely:

```bash
$  curl -k -H "Host: svc1.example.com"  -w "\n" https://$GATEWAY_IP/version
   RBAC: access denied
```

The error indicates we did not send in the required header.   In the next setp, we will use a small *sample* client library to acquire a JWT.  You can also use google OIDC tokens or any other provider (Firebase, Auth0)

The policy above looks for a specific issuer and audience value.  THe `jwksUri` field maps to the public certificate set for our service account.  THe well known url for the service account for Google Cloud is:

`https://www.googleapis.com/service_accounts/v1/jwk/<serviceAccountEmail>`


```bash
pip install -r requirements.txt
python main.py
```

The command line utility will generate two tokens with different specifications.  For Alice, 
.

```json
{
  "iss": "source-service-account@fabled-ray-104117.iam.gserviceaccount.com",
  "iat": 1571185182,
  "sub": "alice",
  "exp": 1571188782,
  "aud": "https://svc1.example.com"
}
```

And Bob
```json
{
  "groups": [
    "group1",
    "group2"
  ],
  "sub": "bob",
  "exp": 1571188782,
  "iss": "source-service-account@fabled-ray-104117.iam.gserviceaccount.com",
  "iat": 1571185182,
  "aud": "https://svc2.example.com"
}
```

Bob, no groups
```json
{
  "iss": "source-service-account@fabled-ray-104117.iam.gserviceaccount.com",
  "iat": 1571185734,
  "sub": "bob",
  "exp": 1571189334,
  "aud": "https://svc2.example.com"
}
```

Export these values as environment variables
```
export TOKEN_ALICE=<tokenvaluealice>
export TOKEN_BOB=<tokenvaluebob>
export TOKEN_BOB_NO_GROUPS=<tokenvaluebob2>
```

>> **WARNING**  the sample code to generate the jwt at the client side uses a service account JWT where the client itself is minting the JWT specifications (meaning it can setup any claimsets it wants, any `sub` field.). In reality, you wouild want to use some other mechanism to acquire a token (Auth0, Firebase Custom Claims, etc).


Now inject the token into the `Authorization: Bearer` header and try to access the protected service:

```bash
for i in {1..1000}; do curl -k -H "Host: svc1.example.com" -H "Authorization: Bearer $TOKEN_ALICE" -w "\n" https://$GATEWAY_IP/version; sleep 1; done
```

The request should now pass validation and you're in.  What we just did is have one policy that globally to the ingress-gateway.  Note, we also applied per-service policies in `auth-policy.yaml` that checks for the `aud:` value in the inbound token.

What that means is if you use Alice's token to access `svc2`, you'll see an authentication validation error because that token doesn't have `"https://svc2.example.com"` in the audience

```
$ curl -k -H "Host: svc2.example.com" -H "Authorization: Bearer $TOKEN_ALICE" -w "\n" https://$GATEWAY_IP/version
   Audiences in Jwt are not allowed
```

In our example, we had a self-signed JWT locally meaning if the end-user had a service account capable of singing, they coudl setup any audience value (i.,e Alice could create a JWT token with the audience of `svc`).  We need to back up and apply addtional controls through RBAC.

##### Authorization using JWT Claims

The other way is to push the allow/deny decision down from Authentication to Authorization and then using claims on the Authz polic 

In `auth-policy.yaml`, uncomment the in the `AuthorizationPolicy` which checks for the correct audience value in the inbound token and apply

```
kubectl apply -f auth-policy.yaml
```

Consider we have two JWT tokens for `Bob`:

One with groups
```json
{
  "groups": [
    "group1",
    "group2"
  ],
  "sub": "bob",
  "exp": 1571188782,
  "iss": "source-service-account@fabled-ray-104117.iam.gserviceaccount.com",
  "iat": 1571185182,
  "aud": "https://svc2.example.com"
}
```

And one without
```json
{
  "iss": "source-service-account@fabled-ray-104117.iam.gserviceaccount.com",
  "iat": 1571185734,
  "sub": "bob",
  "exp": 1571189334,
  "aud": "https://svc2.example.com"
}
```

Both Tokens allow access through to the serivce because they pass authentication (the audience and subject):
```bash
$ curl -sk -H "Host: svc2.example.com" -H "Authorization: Bearer $TOKEN_BOB" -o /dev/null -w "%{http_code}\n"  https://$GATEWAY_IP/version
  200

$ curl -sk -H "Host: svc2.example.com" -H "Authorization: Bearer $TOKEN_BOB_NO_GROUPS" -o /dev/null -w "%{http_code}\n"  https://$GATEWAY_IP/version
  200
```

But what we want to do is deny a request if the token does not include the group header (i know, if Bob had the service account file, he could "just set it"...anyway)

For now, edit `auth-policy.yaml` and modify the authorization policy for the backend service to make sure the groups are specified and the groups claims are set

```yaml
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
 name: svc2-az
spec:
 selector:
   matchLabels:
     app: svc2
 rules:
 - to:
   - operation:
       methods: ["GET"]
   when:
   - key: request.auth.claims[iss]
     values: ["sa-istio@mineral-minutia-820.iam.gserviceaccount.com"]
   - key: request.auth.claims[aud]
     values: ["https://svc2.example.com"]
   - key: request.auth.claims[groups]
     values: ["group1", "group2"]
   - key: request.auth.claims[sub]
     values: ["bob"]
```

Wait maybe 30seconds (it takes time for the policy to propagte)

Once you set that, only Alice should be able to access `svc1` and only Bob access `svc2` except when no group info is provided in the JWT

```bash
$ curl -sk -H "Host: svc1.example.com" -H "Authorization: Bearer $TOKEN_ALICE"  -w "%{http_code}\n" https://$GATEWAY_IP/version
  200

$ curl -sk -H "Host: svc2.example.com" -H "Authorization: Bearer $TOKEN_ALICE"   -w "%{http_code}\n" https://$GATEWAY_IP/version
  403
  Audiences in Jwt are not allowed

$ curl -sk -H "Host: svc1.example.com" -H "Authorization: Bearer $TOKEN_BOB"   -w "%{http_code}\n" https://$GATEWAY_IP/version
  403
  Audiences in Jwt are not allowed

$ curl -sk -H "Host: svc2.example.com" -H "Authorization: Bearer $TOKEN_BOB" -o /dev/null -w "%{http_code}\n" https://$GATEWAY_IP/version
  200

$ curl -sk -H "Host: svc2.example.com" -H "Authorization: Bearer $TOKEN_BOB_NO_GROUPS" -o /dev/null --w "%{http_code}\n"  https://$GATEWAY_IP/version
  403
  RBAC: access denied
```

Notice that bob was only allowed in when the token carried group info.

#### Service to Service and Authentication Policy

In this section, we extend the working set to allow Alice and Bob to access frontend services and ALSO setup an RBAC policy that allows `svcA` to access `svcB`.


When we deployed the application, we associated a service account with each workoad
```yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: svc1-sa
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: svc2-sa
---
```

We can use this service acount to say: 'only allow requests from svc1-sa to access svc2'.  We do this by placing another `AuthorizationPolicy` policy rule in for `svc2`

```yaml
 - from:
   - source:
       principals: ["cluster.local/ns/default/sa/svc1-sa"] 
```       
 That is, 

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
 name: svc2-az
spec:
 selector:
   matchLabels:
     app: svc2
 rules:
 - from:
   - source:
       principals: ["cluster.local/ns/default/sa/svc1-sa"] 
   to:
   - operation:
       methods: ["GET"]
   when:
   - key: request.auth.claims[iss]
     values: ["sa-istio@mineral-minutia-820.iam.gserviceaccount.com"]
   - key: request.auth.claims[aud]
     values: ["https://svc2.example.com"]
   - key: request.auth.claims[groups]
     values: ["group1", "group2"]
   - key: request.auth.claims[sub]
     values: ["bob"]
```

Now, if bob tries to access `svc2` externally even with a correct token, he will see

```bash
$ curl -sk -H "Host: svc2.example.com" -H "Authorization: Bearer $TOKEN_BOB"  -w "%{http_code}\n" https://$GATEWAY_IP/version
  RBAC: access denied
```

Let try to exc **into** a pod where `svc1` is running and access `svc2`:

```bash
$ kubectl get po
NAME                    READY   STATUS    RESTARTS   AGE
svc1-7489fbf8d4-8tffm   2/2     Running   0          92m
svc2-7b4d7566cb-jlmlm   2/2     Running   0          92m


$ kubectl exec -ti svc1-7489fbf8d4-8tffm -- /bin/bash
```

First try to access the backend service:

```bash
curl -s -w "%{http_code}\n"  http://svc2.default.svc.cluster.local:8080/version
403
RBAC: access denied
```

You'll see a 403 because although the request was inbound from `svc1` which is using PEER authentication, we did not add Bob's JWT token.  So set an env-var and execute the request again:
```
root@svc1-7489fbf8d4-8tffm:/# export TOKEN_BOB=eyJhbGciOi...

root@svc1-7489fbf8d4-8tffm:/# curl -s -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_BOB" http://svc2.default.svc.cluster.local:8080/version
200
```

You are now in!

This is a bit silly since we needed to use the JWT token for bob for just service to serice traffic.

You dont' ofcourse need to do that: just edit the `AuthorizationPolicy` for `svc2` and comment out

```yaml
   when:
   - key: request.auth.claims[iss]
     values: ["sa-istio@mineral-minutia-820.iam.gserviceaccount.com"]
   - key: request.auth.claims[aud]
     values: ["https://svc2.example.com"]
   - key: request.auth.claims[groups]
     values: ["group1", "group2"]
   - key: request.auth.claims[sub]
     values: ["bob"]
```
Bob can't access `svc2` from the outside but `svc1` can access `svc2`



```bash
# from external -> svc1
curl -sk -H "Host: svc2.example.com" -H "Authorization: Bearer $TOKEN_BOB"  -w "%{http_code}\n" https://$GATEWAY_IP/version
403
RBAC: access denied

# from svc1->svc
curl -s -w "%{http_code}\n"  http://svc2.default.svc.cluster.local:8080/version
200
```

### External Authorization HTTPFilter

You can also setup `envoy.ext_authz` Filter in this cluster.  When using the `ext_authz` filter on the frontend service, any request for `app: myapp, version: v1` will undergo an external authorization check by a serivce you run elsewhere.    The external serivice will only allow a request through if it carries `Authorizaton: Bearer foo` in the  header.


```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: ext-authz-filter
spec:
  workloadLabels:
    app: myapp
    version: v1
  filters:
  - listenerMatch:
      portNumber: 8080
      listenerType: SIDECAR_INBOUND
    filterName: envoy.ext_authz
    filterType: HTTP
    filterConfig:
      grpc_service:
        google_grpc:
           target_uri: "ip_of_your_authz_server:50051"
           stat_prefix: "ext_authz"
```

To use this type of authorization check, you will need to run a serivce somewhere (either within istio or external to istio).  The following runs the serivce external to istio:

- [Istio External Authorization Server](https://github.com/salrashid123/istio_external_authorization_server)
- [Envoy External Authorization server (envoy.ext_authz) HelloWorld](https://github.com/salrashid123/envoy_external_authz)

First spin up a GCP VM that has an external IP, install golang there and startup the `authz` server in the git repo provided.  You'll also need to open up port `:50051` to that VM.  

After that, add in the ip address of yoru vm to the yaml file and apply the envoy filter:

```bash
kubectl apply -f  istio-fev1-httpfilter-ext_authz.yaml
```

Once you do that, every request to the fronend service will fail unless the specific header is sent through.

>> Note you'll ofcourse not want to run this serivce anywhere thas externally accessible!...this is just for a demo!!

THis is what an inbound request from istio to the authorization server may look like:

```bash
$ go run grpc_server.go
2020/02/20 20:41:40 Starting gRPC Server at :50051
2020/02/20 20:42:41 >>> Authorization called check()
2020/02/20 20:42:41 Inbound Headers:
2020/02/20 20:42:41 {
  ":authority": "35.238.81.95",
  ":method": "GET",
  ":path": "/version",
  "accept": "*/*",
  "authorization": "Bearer foo",
  "content-length": "0",
  "user-agent": "curl/7.66.0",
  "x-b3-sampled": "0",
  "x-b3-spanid": "b228f9e2179794c5",
  "x-b3-traceid": "725c448565d59423b228f9e2179794c5",
  "x-envoy-internal": "true",
  "x-forwarded-client-cert": "By=spiffe://cluster.local/ns/default/sa/myapp-sa;Hash=ae6b57b6ce2932c74b54c40c5e1a7a13daf2828edeb688f9d273a6ea54f38dbf;Subject=\"\";URI=spiffe://cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account",
  "x-forwarded-for": "10.128.0.61",
  "x-forwarded-proto": "https",
  "x-istio-attributes": "CiMKGGRlc3RpbmF0aW9uLnNlcnZpY2UubmFtZRIHEgVteWFwcAoqCh1kZXN0aW5hdGlvbi5zZXJ2aWNlLm5hbWVzcGFjZRIJEgdkZWZhdWx0Ck4KCnNvdXJjZS51aWQSQBI+a3ViZXJuZXRlczovL2lzdGlvLWluZ3Jlc3NnYXRld2F5LTk3ZGNkN2Y4Ny02MnpjZC5pc3Rpby1zeXN0ZW0KPQoYZGVzdGluYXRpb24uc2VydmljZS5ob3N0EiESH215YXBwLmRlZmF1bHQuc3ZjLmNsdXN0ZXIubG9jYWwKOwoXZGVzdGluYXRpb24uc2VydmljZS51aWQSIBIeaXN0aW86Ly9kZWZhdWx0L3NlcnZpY2VzL215YXBw",
  "x-request-id": "e7932678-b3a2-40b8-bc49-6b645448ae28"
}
```


## Cleanup

The easiest way to clean up what you did here is to delete the GKE cluster!

```
gcloud container clusters delete cluster-1
```

## Conclusion

The steps i outlined above is just a small set of what Istio has in store.  I'll keep updating this as it move towards ```1.0``` and subsequent releases.

If you find any are for improvements, please submit a comment or git issue in this [repo](https://github.com/salrashid123/istio_helloworld),.
---
