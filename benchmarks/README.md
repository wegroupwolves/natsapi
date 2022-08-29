# Benchmarks

## Results

### Rest

GET /rest/index

```
Server Software:        uvicorn
Server Hostname:        localhost
Server Port:            5000

Document Path:          /rest/index
Document Length:        17 bytes

Concurrency Level:      100
Time taken for tests:   10.171 seconds
Complete requests:      1000
Failed requests:        0
Total transferred:      161000 bytes
HTML transferred:       17000 bytes
Requests per second:    98.32 [#/sec] (mean)
Time per request:       1017.057 [ms] (mean)
Time per request:       10.171 [ms] (mean, across all concurrent requests)
Transfer rate:          15.46 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    1   3.0      0      14
Processing:    83 1005  95.8   1018    1213
Waiting:       64  988  88.3    993    1192
Total:         84 1007  95.9   1018    1213

Percentage of the requests served within a certain time (ms)
  50%   1018
  66%   1030
  75%   1038
  80%   1075
  90%   1103
  95%   1192
  98%   1199
  99%   1201
 100%   1213 (longest request)
```

POST /rest/sum

```
Server Software:        uvicorn
Server Hostname:        localhost
Server Port:            5000

Document Path:          /rest/sum
Document Length:        3 bytes

Concurrency Level:      100
Time taken for tests:   10.328 seconds
Complete requests:      1000
Failed requests:        0
Total transferred:      146000 bytes
Total body sent:        184000
HTML transferred:       3000 bytes
Requests per second:    96.82 [#/sec] (mean)
Time per request:       1032.849 [ms] (mean)
Time per request:       10.328 [ms] (mean, across all concurrent requests)
Transfer rate:          13.80 [Kbytes/sec] received
                        17.40 kb/s sent
                        31.20 kb/s total

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    1   0.7      0       3
Processing:    14 1026  85.3   1008    1212
Waiting:       11 1014  80.8    998    1209
Total:         14 1026  85.6   1008    1214
WARNING: The median and mean for the initial connection time are not within a normal deviation
        These results are probably not that reliable.

Percentage of the requests served within a certain time (ms)
  50%   1008
  66%   1054
  75%   1070
  80%   1071
  90%   1161
  95%   1162
  98%   1214
  99%   1214
 100%   1214 (longest request)
```

### Nats

GET /nats/index

```
Server Software:        uvicorn
Server Hostname:        localhost
Server Port:            5000

Document Path:          /nats/index
Document Length:        17 bytes

Concurrency Level:      100
Time taken for tests:   0.739 seconds
Complete requests:      1000
Failed requests:        0
Total transferred:      161000 bytes
HTML transferred:       17000 bytes
Requests per second:    1354.05 [#/sec] (mean)
Time per request:       73.852 [ms] (mean)
Time per request:       0.739 [ms] (mean, across all concurrent requests)
Transfer rate:          212.89 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    1   2.3      1      11
Processing:    22   70  42.7     52     197
Waiting:        6   60  41.9     44     189
Total:         22   72  44.7     53     204

Percentage of the requests served within a certain time (ms)
  50%     53
  66%     54
  75%     59
  80%     88
  90%    182
  95%    203
  98%    203
  99%    204
 100%    204 (longest request)
```

POST /nats/sum

```
Server Software:        uvicorn
Server Hostname:        localhost
Server Port:            5000

Document Path:          /nats/sum
Document Length:        1 bytes

Concurrency Level:      100
Time taken for tests:   0.738 seconds
Complete requests:      1000
Failed requests:        0
Total transferred:      144000 bytes
Total body sent:        184000
HTML transferred:       1000 bytes
Requests per second:    1355.88 [#/sec] (mean)
Time per request:       73.753 [ms] (mean)
Time per request:       0.738 [ms] (mean, across all concurrent requests)
Transfer rate:          190.67 [Kbytes/sec] received
                        243.64 kb/s sent
                        434.31 kb/s total

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    1   0.7      1       4
Processing:     8   72  12.6     68     103
Waiting:        2   62  13.3     58      97
Total:          8   72  12.5     68     103

Percentage of the requests served within a certain time (ms)
  50%     68
  66%     70
  75%     70
  80%     79
  90%    100
  95%    101
  98%    103
  99%    103
 100%    103 (longest request)
```

## Conclusion

Nats is quite a lot faster than using http.
