//var agent = require('@google-cloud/trace-agent').start();

const express = require('express');

const app = express();
var rp = require('request-promise');
const dns = require('dns');
const morgan = require('morgan');

const port = 8080;
//process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

app.use(
  morgan('combined')
);

var winston = require('winston');
var logger = winston.createLogger({
  transports: [
    new (winston.transports.Console)({ level: 'info' })
  ]
 });

app.get('/', (request, response) => {
  logger.info('Called /');
  response.send('Hello from Express!');
})

app.get('/_ah/health', (request, response) => {
  response.send('ok');
})

app.get('/varz', (request, response) => {
  response.send(process.env);
})

app.get('/version', (request, response) => {
  response.send(process.env.VER);
})

app.get('/backend', (request, response) => {
  response.send('pod: [' + process.env.MY_POD_NAME + ']    node: [' + process.env.MY_NODE_NAME + ']');
})

app.get('/hostz', (request, response) => {
  dns.resolveSrv("_http._tcp.be.default.svc.cluster.local",  function onLookup(err, addresses, family) {

      if (err) {
        response.send(err);
      } else if (addresses.length >= 1) {
        logger.info('addresses: ' + JSON.stringify(addresses));        
        var host = addresses[0].name;
        var port = addresses[0].port;
        logger.info(host + " --> " + port);

        var resp_promises = []
        var urls = [
                    'http://' + host + ':' + port + '/backend',
        ]
    
        urls.forEach(function(element){
          resp_promises.push( getURL(element) )
        });
    
        Promise.all(resp_promises).then(function(value) {
          response.send(value);
        }, function(value) {
          response.send(value);
        });

      } else{
        response.send('No Backend Services found');
      }
  });
})

function getURL(u) {
  var options = {
    method: 'GET',
    uri: u,
    resolveWithFullResponse: true,
    simple: false,
  };
  return rp(options)
    .then(function (resp) {
        return Promise.resolve(
          { 'url' : u, 'body': resp.body, 'statusCode': resp.statusCode }
        );
    })
    .catch(function (err) {
        return Promise.resolve({ 'url' : u, 'statusCode': err } );
    });
}

app.get('/requestz', (request, response) => {

    var resp_promises = []
    var urls = [
                'http://www.cnn.com:443/',
                'http://www.bbc.com:443/robots.txt',
                'https://www.bbc.com/robots.txt',
    ]

    urls.forEach(function(element){
      resp_promises.push( getURL(element) )
    });

    Promise.all(resp_promises).then(function(value) {
      response.send(value);
    }, function(value) {
      response.send(value);
    });
})

app.listen(port, (err) => {
  if (err) {
    return logger.error('something bad happened', err)
  }
  logger.info(`server is listening on ${port}`)
})