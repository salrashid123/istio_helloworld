# Istio "Hello World" my way

## What is this repo?

This is a really simple application I wrote over holidays a couple weeks back that detail my experiences and
feedback.  To be clear, its a really, really basic NodeJS application that i used but more importantly, it covers
the main sections of [Istio](https://istio.io/) that i was seeking to understand better (if even just as a helloworld).  

I do know isito has the "[bookinfo](https://github.com/istio/istio/tree/master/samples/bookinfo)" application but the best way
i understand something is to rewrite sections and only those sections from the ground up.

## What i tested

- Basic istio Installation on Google Kubernetes Engine.
- Grafana
- Prometheus
- SourceGraph
- Jaeger
- Route Control
- Destination Rules
- Egress Policies


## What is the app you used?

NodeJS in a Dockerfile...something really minimal.  You can find the entire source under the 'nodeapp' folder in this repo.

The endpoints on this app are as such:

- ```/```:  Does nothing;  ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L24))
- ```/varz```:  Returns all the environment variables on the current Pod ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L33))
- ```/version```: Returns just the "process.env.VER" variable that was set on the Deployment ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L37))
- ```/backend```: Return the nodename, pod name.  Designed to only get called as if the applciation running is a 'backend' ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L41))
- ```/hostz```:  Does a DNS SRV lookup for the 'backend' and makes an http call to its '/backend', endpoint ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L45))
- ```/requestz```:  Makes an HTTP fetch for three external URLs (used to show egress rules) ([source](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L95))


I build and uploaded this app to dockerhub at

```
docker.io/salrashid123/istioinit:1
docker.io/salrashid123/istioinit:2
```
(to simulat two release version of an app ...yeah, theyr'e the same app but during deployment i set an env-var directly):


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

### Create a 1.10+ GKE Cluster and Bootstrap Istio


```bash

gcloud container  clusters create cluster-1 --machine-type "n1-standard-1" --cluster-version=1.10.5 --zone us-central1-a  --num-nodes 4

gcloud container clusters get-credentials cluster-1 --zone us-central1-a

kubectl create clusterrolebinding cluster-admin-binding --clusterrole=cluster-admin --user=$(gcloud config get-value core/account)

kubectl create ns istio-system

export ISTIO_VERSION=1.0.0-snapshot.2
wget https://github.com/istio/istio/releases/download/$ISTIO_VERSION/istio-$ISTIO_VERSION-linux.tar.gz
tar xvzf istio-$ISTIO_VERSION-linux.tar.gz

wget https://storage.googleapis.com/kubernetes-helm/helm-v2.9.1-linux-amd64.tar.gz
tar xzvf helm-v2.9.1-linux-amd64.tar.gz

export PATH=$PATH:`pwd`/istio-$ISTIO_VERSION/bin:`pwd`/linux-amd64/

helm template istio-$ISTIO_VERSION/install/kubernetes/helm/istio --name istio --namespace istio-system \
   --set prometheus.enabled=true \
   --set servicegraph.enabled=true \
   --set grafana.enabled=true \
   --set tracing.enabled=true \
   --set sidecar-injector.enabled=true \
   --set global.proxy.image=proxyv2 \
   --set global.mtls.enabled=true > istio.yaml

kubectl create -f istio.yaml
kubectl label namespace default istio-injection=enabled
```

Wait maybe 2 to 3 minutes and make sure all the Deployments are live:

### Make sure the Istio installation is ready

Verify this step by makeing sure all the ```Deployments``` are Available.

```bash
$ kubectl get no,po,rc,svc,ing,deployment -n istio-system
NAME                                          STATUS    ROLES     AGE       VERSION
no/gke-cluster-1-default-pool-589c748e-3fl4   Ready     <none>    4m        v1.10.5-gke.0
no/gke-cluster-1-default-pool-589c748e-5dpj   Ready     <none>    4m        v1.10.5-gke.0
no/gke-cluster-1-default-pool-589c748e-ccbd   Ready     <none>    4m        v1.10.5-gke.0
no/gke-cluster-1-default-pool-589c748e-htk8   Ready     <none>    4m        v1.10.5-gke.0

NAME                                          READY     STATUS    RESTARTS   AGE
po/grafana-546f5b7566-b2gh7                   1/1       Running   0          1m
po/istio-citadel-85fcc767fc-952wl             1/1       Running   0          1m
po/istio-egressgateway-96b7679d5-mj2fh        1/1       Running   0          1m
po/istio-galley-5f5f9b9676-b64d4              1/1       Running   0          1m
po/istio-ingress-787bb7c94b-lq6pz             1/1       Running   0          1m
po/istio-ingressgateway-7f7d758d65-wngk6      1/1       Running   0          1m
po/istio-pilot-6db8d59464-x2j8s               2/2       Running   0          1m
po/istio-policy-7b978cf7df-gtnld              2/2       Running   0          1m
po/istio-sidecar-injector-855f88c954-btnss    1/1       Running   0          1m
po/istio-statsd-prom-bridge-59b45fd6d-vz9sp   1/1       Running   0          1m
po/istio-telemetry-7dfcc797b6-grhc5           2/2       Running   0          1m
po/istio-tracing-647f8c48f8-zdwwf             1/1       Running   0          1m
po/prometheus-ffd95f9f6-8q9wn                 1/1       Running   0          1m
po/servicegraph-55b7fcd48d-wsbmp              1/1       Running   0          1m

NAME                           TYPE           CLUSTER-IP      EXTERNAL-IP     PORT(S)                                                                     AGE
svc/grafana                    ClusterIP      10.11.253.43    <none>          3000/TCP                                                                    1m
svc/istio-citadel              ClusterIP      10.11.240.31    <none>          8060/TCP,9093/TCP                                                           1m
svc/istio-egressgateway        ClusterIP      10.11.252.74    <none>          80/TCP,443/TCP                                                              1m
svc/istio-galley               ClusterIP      10.11.242.73    <none>          443/TCP,9093/TCP                                                            1m
svc/istio-ingress              LoadBalancer   10.11.246.248   <pending>       80:32000/TCP,443:30899/TCP                                                  1m
svc/istio-ingressgateway       LoadBalancer   10.11.241.167   35.202.138.64   80:31380/TCP,443:31390/TCP,31400:31400/TCP,15011:30016/TCP,8060:32469/TCP   1m
svc/istio-pilot                ClusterIP      10.11.244.184   <none>          15003/TCP,15005/TCP,15007/TCP,15010/TCP,15011/TCP,8080/TCP,9093/TCP         1m
svc/istio-policy               ClusterIP      10.11.241.210   <none>          9091/TCP,15004/TCP,9093/TCP                                                 1m
svc/istio-sidecar-injector     ClusterIP      10.11.241.157   <none>          443/TCP                                                                     1m
svc/istio-statsd-prom-bridge   ClusterIP      10.11.249.19    <none>          9102/TCP,9125/UDP                                                           1m
svc/istio-telemetry            ClusterIP      10.11.243.165   <none>          9091/TCP,15004/TCP,9093/TCP,42422/TCP                                       1m
svc/prometheus                 ClusterIP      10.11.250.133   <none>          9090/TCP                                                                    1m
svc/servicegraph               ClusterIP      10.11.241.17    <none>          8088/TCP                                                                    1m
svc/tracing                    ClusterIP      10.11.254.79    <none>          80/TCP                                                                      1m
svc/zipkin                     ClusterIP      10.11.253.22    <none>          9411/TCP                                                                    1m

NAME                              DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
deploy/grafana                    1         1         1            1           1m
deploy/istio-citadel              1         1         1            1           1m
deploy/istio-egressgateway        1         1         1            1           1m
deploy/istio-galley               1         1         1            1           1m
deploy/istio-ingress              1         1         1            1           1m
deploy/istio-ingressgateway       1         1         1            1           1m
deploy/istio-pilot                1         1         1            1           1m
deploy/istio-policy               1         1         1            1           1m
deploy/istio-sidecar-injector     1         1         1            1           1m
deploy/istio-statsd-prom-bridge   1         1         1            1           1m
deploy/istio-telemetry            1         1         1            1           1m
deploy/istio-tracing              1         1         1            1           1m
deploy/prometheus                 1         1         1            1           1m
deploy/servicegraph               1         1         1            1           1m
```


### Make sure the Istio an IP for the ```LoadBalancer``` is assigned:

Run

```
kubectl get svc istio-ingressgateway -n istio-system

export GATEWAY_IP=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo $GATEWAY_IP
```

Note down the ```$GATEWAY_IP```; we will use this later as the entrypoint into the helloworld app

### Setup some tunnels to each of the services:

Open up three new shell windows and type in one line into each:
```
kubectl -n istio-system port-forward $(kubectl -n istio-system get pod -l app=grafana -o jsonpath='{.items[0].metadata.name}') 3000:3000

kubectl -n istio-system port-forward $(kubectl -n istio-system get pod -l app=servicegraph -o jsonpath='{.items[0].metadata.name}') 8088:8088

kubectl port-forward -n istio-system $(kubectl get pod -n istio-system -l app=jaeger -o jsonpath='{.items[0].metadata.name}') 16686:16686 
```

Open up a browser (three tabs) and go to:
- ServiceGraph http://localhost:8088/dotviz
- Grafana http://localhost:3000/dashboard/db/istio-dashboard
- Jaeger http://localhost:16686


### Deploy the sample application 

The default ```all-istio.yaml``` runs:

- Ingress with SSL
- Deployments:
- - myapp-v1:  1 replica
- - myapp-v2:  1 replica
- - be-v1:  1 replicas
- - be-v2:  1 replicas

basically, a default frontend-backend scheme with two replicas each and the same 'v1' verison.

> Note: the default yaml pulls and run my dockerhub image- feel free to change this if you want.


```
kubectl create -f all-istio.yaml
```

now use ```istioctl``` to create the ingress-gateway:


```
istioctl create -f istio-ingress-gateway.yaml
```

and then initialize istio on a sample application

```
istioctl create -f istio-fev1-bev1.yaml
```

Wait until the deployments complete:

```
$ kubectl get po,deployments,svc,ing
NAME                           READY     STATUS    RESTARTS   AGE
po/be-v1-68947fc994-k8sv2      2/2       Running   0          1m
po/be-v2-75fb685fcb-pv8rx      2/2       Running   0          1m
po/myapp-v1-5c4467779d-n5qg5   2/2       Running   0          1m
po/myapp-v2-5584cff6bb-p666g   2/2       Running   0          1m

NAME              DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
deploy/be-v1      1         1         1            1           1m
deploy/be-v2      1         1         1            1           1m
deploy/myapp-v1   1         1         1            1           1m
deploy/myapp-v2   1         1         1            1           1m

NAME             TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
svc/be           ClusterIP   10.11.251.53    <none>        8080/TCP   1m
svc/kubernetes   ClusterIP   10.11.240.1     <none>        443/TCP    7m
svc/myapp        ClusterIP   10.11.246.173   <none>        8080/TCP   1m
```

Notice that each pod has two containers:  one is from isto, the other is the applicaiton itself (this is because we have automatic sidecar injection enabled).

Also note that in ```all-istio.yaml``` we did not define an ```Ingress``` object though we've defined a TLS secret with a very specific metadata name: ```istio-ingressgateway-certs```.  That is a special name for a secret that is used by Istio to setup its own ingress gateway:


#### Ingress Gateway Secret in 1.0.0

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

```
export GATEWAY_IP=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo $GATEWAY_IP
```

### Send Traffic 

This section shows basic user->frontend traffic and how serviceGrpah and Grafana consoles:

#### Frontend only

So...lets send traffic with the ip; (the ```/varz``` endpoint will send traffic to the frontend service only)

```bash
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version; sleep 1; done
```

You should see a sequence of 1's indicating the version of the frontend ```/version``` you just hit
```
111111111111111111111111111111111
```
(source: [/version](https://github.com/salrashid123/istio_helloworld/blob/master/nodeapp/app.js#L37) endpoint)

You should also see on servicegraph:

![alt text](images/svc_fev1.png)

and

![alt text](images/grafana_fev1.png)


#### Frontend and Backend

Now the next step in th exercise:

to send requests to ```user-->frontend--> backend```;  we'll use the applications ```/hostz``` endpoint to do that.

(note i'm using  [jq](https://stedolan.github.io/jq/) utility to parse JSON)

```
for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; done
```

you should see output indicating traffic from the v1 backend verison: ```be-v1-*```

```
for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; done
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
```

Note both ServiceGraph and Grafana shows both frontend and backend service telemetry and that traffic to ```be:v1``` is 0 req/s 

![alt text](images/svc_fev1_bev1.png)


![alt text](images/grafana_fev1_bev1.png)

## Route Control

This section details how to slectively send traffic to service ```versions```

### Selective Traffic

In this sequence,  we will setup a routecontrol to:

1. Send all traffic to ```myapp:v1```.  
2. traffic from ```myapp:v1``` to be can only go to ```be:v2```

The yaml on ```istio-fev1-bev2.yaml``` would direct inbound traffic for ```myapp:v1``` to go to ```be:v2``` (note the ```sourceLabels:``` part that specifies requests inbound from ```myapp:v1```).  The snippet for this config is:

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

Then setup the config with istioctl:

```
istioctl replace -f istio-fev1-bev2.yaml
```

After sending traffic to check which backend system was called ```/hostz```, we see responses from only ```be-v2-*```.
What the ```/hosts``` endpoint does is takes a users request to ```fe-*``` and targets any ```be-*```.  Since we only have ```fe-v1``` instances
running, the traffic outbound for ```be-*``` must terminate at a ```be-v2``` version given the rule above:

```
for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; done
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
```

and on the frontend version is always one.
```
for i in {1..100}; do curl -k https://$GATEWAY_IP/version; sleep 1; done
11111111111111111111111111111
```

Note the traffic to ```be-v1``` is 0 while there is a non-zero traffic to ```be-v2``` from ```fe-v1```:

![alt text](images/route_fev1_bev2.png)

![alt text](images/grafana_fev1_bev2.png)


If we now overlay rules that direct traffic allow interleaved  ```fe(v1|v2) -> be(v1|v2)``` we expect to see requests to both frontend v1 and backend
```
istioctl replace -f istio-fev1v2-bev1v2.yaml
```

then frontend is both v1 and v2:
```
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version;  done
111211112122211121212211122211
```

and backend is responses comes from both be-v1 and be-v2

```
for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body';  done
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-3fl4]"
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-3fl4]"
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
"pod: [be-v1-68947fc994-k8sv2]    node: [gke-cluster-1-default-pool-589c748e-3fl4]"
"pod: [be-v2-75fb685fcb-pv8rx]    node: [gke-cluster-1-default-pool-589c748e-htk8]"
```

![alt text](images/route_fev1v2_bev1v2.png)

![alt text](images/grafana_fev1v2_bev1v2.png)


### Route Path

Now lets setup a more selective route based on a specific path in the URI:

- Route requests to myapp where path=/version to only ```v1```
  A request to ```http://gateway_ip/version``` will go to ```v1``` only


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


```
istioctl replace -f istio-route-version-fev1-bev1v2.yaml
```

```
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version; done
1111111111111111111
```

You may have noted how the route to the destination is weighted split vs delcared round robin (eg:)
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

Normally, you can use that destination rule to split traffic between services alltogether (eg, in real life you may have):
```yaml
  - route: 
    - destination:
        host: app1
        subset: v1
      weight: 50
    - destination:
        host: app2
        subset: v10
      weight: 50
```

which for any other endpoint other than endpoint other thatn ```/version```, each request is split 50/50 between two destination services (```app1``` and ```app2```)


Anyway, now lets edit rule to  and change the prefix match to ```/xversion``` so the match doesn't apply 
  A request to http://gateway_ip/version will go to v1 and v2 (since the path rule did not match)

Once you make this change, use ```istioctl``` to make the change happen

```
istioctl replace -f istio-route-version-fev1-bev1v2.yaml
```


```kubectl delete -f all-istio.yaml```

```
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version; sleep 1; done
2121212222222222222221122212211222222222222222
```

What you're seeing is ```myapp-v1``` now getting about 20% of the traffic while ```myapp-v2``` gets 80%

### Destination Rules

These rules sends all traffic from ```myapp-v1``` round-robin to both version of the backend.

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
istioctl replace -f istio-fev1-bev1v2.yaml
```

you'll see frontend request all going to ```fe-v1```

```
for i in {1..1000}; do curl -k  https://$GATEWAY_IP/version; sleep 1; done
11111111111111
```

with backend requests coming from pretty much round robin

```bash
for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; sleep 1; done
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
```

Now change the ```istio-fev1-bev1v2.yaml```  to ```RANDOM``` and see response is from v1 and v2 random:
```bash
for i in {1..1000}; do curl -s -k https://$GATEWAY_IP/hostz | jq '.[0].body'; sleep 1; done
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
"pod: [be-v2-9dd4cf9b8-q7zbn]    node: [gke-cluster-1-default-pool-195daff5-r8pl]"
"pod: [be-v1-5bc4cc7f6b-pqpkf]    node: [gke-cluster-1-default-pool-195daff5-5sfm]"
```

### Egress Rules


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
  - number: 443
    name: https
    protocol: HTTP
---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: bbc-ext
spec:
  host: www.bbc.com
  trafficPolicy:
    tls:
      mode: SIMPLE
```


Allows only ```https://www.bbc.com/*``` but here is the catch:  you must change your code in the container to make a call to

```http://www.bbc.com:443```  (NOTE the protocol is different)

This is pretty unusable ..futurue releases of egress+istio will use SNI so users do not have to change their client code like this.

Anyway, to test, the `/hostz` endpoint tries to fetch the following URLs:

```javascript
    var urls = [
                'http://www.cnn.com:443/',
                'http://www.bbc.com:443/robots.txt',
                'https://www.bbc.com/robots.txt',
    ]
```

Lets setup this customer for these egress rules.

First make sure there is an inbound rule already running:

```
istioctl replace -f istio-fev1-bev1.yaml
```


- Without egress rule, each request will fail:

```
curl -k -s  https://$GATEWAY_IP/requestz | jq  '.'
```

gives

```
[
  {
    "url": "http:\/\/www.cnn.com:443\/",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  {
    "url": "http:\/\/www.bbc.com:443\/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
  {
    "url": "https:\/\/www.bbc.com\/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: read ECONNRESET",
```

#### With egress rule

then apply the egress policy:

```
istioctl create -f istio-egress-rule.yaml
```


gives

```bash
curl -s -k https://$GATEWAY_IP/requestz | jq  '.'
[
  {
    "url": "http://www.cnn.com:443/",
    "body": "",
    "statusCode": 404
  },
  {
    "url": "http://www.bbc.com:443/robots.txt",
    "body": "# v.4.7.4\n# HTTPS  www.bbc.com\nUser-agent: *\nSitemap: https://www.bbc.com/sitemaps/https-index-com-archive.xml\nSitemap: https://www.bbc.com/sitemaps/https-index-com-news.xml\n\n\nDisallow: /cbbc/search/\nDisallow: /cbbc/search$\nDisallow: /cbbc/search?\nDisallow: /cbeebies/search/\nDisallow: /cbeebies/search$\nDisallow: /cbeebies/search?\nDisallow: /chwilio/\nDisallow: /chwilio$\nDisallow: /chwilio?\nDisallow: /education/blocks$\nDisallow: /education/blocks/\nDisallow: /newsround\nDisallow: /search/\nDisallow: /search$\nDisallow: /search?\nDisallow: /food/favourites\nDisallow: /food/recipes/search*?*",
    "statusCode": 200
  },
  {
    "url": "https://www.bbc.com/robots.txt",
    "statusCode": {
      "name": "RequestError",
      "message": "Error: write EPROTO 140312253028160:error:140770FC:SSL routines:SSL23_GET_SERVER_HELLO:unknown protocol:../deps/openssl/openssl/ssl/s23_clnt.c:827:\n",
      "cause": {
        "errno": "EPROTO",
        "code": "EPROTO",
        "syscall": "write"
      },
      "error": {
        "errno": "EPROTO",
        "code": "EPROTO",
        "syscall": "write"
      },
      "options": {
        "method": "GET",
        "uri": "https://www.bbc.com/robots.txt",
        "resolveWithFullResponse": true,
        "simple": false,
        "transform2xxOnly": false
      }
    }
  }
]

```

Notice that only one of the hosts worked over SSL worked

## Cleanup

The easiest way to clean up what you did here is to delete the GKE cluster!

```
gcloud container clusters delete cluster-1
```

## Conclusion

The steps i outlined above is just a small set of what Istio has in store.  I'll keep updating this as it move towards ```1.0``` and subsequent releases.

If you find any are for improvements, please submit a comment or git issue in this [repo](https://github.com/salrashid123/istio_helloworld),.
---