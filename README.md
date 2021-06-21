# NGINX LOG ANALYZER
***

## Start
1. Name of file to analyze should be
 > nginx-access-ui.log-{YYYYmmdd}(.gz)

2. Format inside
> log_format ui_short: '$remote_addr  $remote_user $http_x_real_ip'
                      '[$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"'
                      '"$http_X_REQUEST_ID" "$http_X_RB_USER" '
                      '$request_time';

## Example of call (run): 

* > $ python log_analyzer.py

will use a default config

```
config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}
```
* **REPORT_SIZE** - number of urls in report
* **REPORT_DIR** - directory for report generation
* **LOG_DIR** - directory where log files are located

First run if _./reports_ and _./log_ doesn't exist, directories will be created

* > $ python log_analyzer.py --config default

will use config from default path ./configuration.txt

* > $ python log_analyzer.py --config configuration.txt

will use config from file 'configuration.txt'

if there are problem with configuration file, the work will be stopped

## Report Creation
To create report use **report.html** with data _"table_json=$table_json"_.
It should be located in **$REPORT_DIR**
If generation of report is success, than **report-yyyy.mm.dd.html** file is created in **$REPORT_DIR** 

## Logging
To log to console don't set _log_path_ in configuration file
* **log_path** - the script logging path

```
log_path = "."
```

If path is found, log **log_analyzer{timestamp}.log** in $log_path will be written.

## Test run
To run test

> $python test_la.py

It will create some files and directory for testing.
It will be deleted after finish.

## Compatibility
Tested by Python 3.8
