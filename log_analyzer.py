#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
****************************************************************************
Created by @olga.rogova
Date: 17/06/2021
****************************************************************************
'''

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip'
#                     '[$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for"'
#                     '"$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';


import sys
import traceback
import os
import shutil
import imp
import logger
import gzip
import re
import datetime
from string import Template
import logging

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}
log_path = '.'
default_path = "./configuration.txt"
error_percent = 50
lineformat = re.compile(r"(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) "
                        r"(?P<remoteuser>(\-)|.+)  - "
                        r"\[(?P<dateandtime>\d{2}\/[a-z]{3}\/\d{4}:"
                        r"\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\] "
                        r"((\"(?P<method>.+) )(?P<url>.+) "
                        r"(http\/[1-2]\.[0-9]\")) "
                        r"(?P<statuscode>\d{3}) (?P<bytessent>\d+) "
                        r"([\"](?P<refferer>(\-)|(.+))[\"]) "
                        r"([\"](?P<useragent>(\-)|.+)[\"]) "
                        r"([\"](?P<forwarded>(\-)|.+)[\"]) "
                        r"([\"](?P<requestid>(\-)|.+)[\"]) "
                        r"([\"](?P<rbuser>(\-)|.+)[\"]) "
                        r"(?P<requesttime>\d+\.\d+)", re.IGNORECASE)


def import_config(pdefaultPath, pinputList):
    """
    Parse options
    :param pdefaultPath: path to default config file
    :param pinputList: sys.argv[1:]
    :return:
    """
    cfg = None
    if len(pinputList) > 1 and '--config' in pinputList:
        file_path = (
            pinputList[pinputList.index('--config') + 1],
            pdefaultPath)[
            pinputList[pinputList.index('--config') + 1].
                lower() == 'default']
        file_path = os.path.join(file_path)
        # Check file existance
        if os.path.isfile(file_path) is True:  # is a file?
            try:
                cfg = imp.\
                    load_source('cfg', file_path)  # load cfg as variable
            except:
                sys.exit(-6)
        else:
            sys.exit(-7)
    elif len(pinputList) == 1:
        sys.exit(-5)
    return cfg


def read_config(pcfg, pcfgIn):
    """
    Make final config by used config and option.config
    :param pcfg: default config (from source)
    :param pcfgIn: if was found --config
    :return: new config or None
    """
    cfg = pcfgIn
    if pcfgIn is None:  # no input config
        res = pcfg
    elif 'config' in cfg.__dict__:  # check "config attr in cfg data"
        res = {key: cfg.config.get(key, pcfg[key])
                   for key in pcfg}  # replace default values by cfg.config
    else:
        logger.error("No 'config' in configuration file ",
                         stack_info=True)
        return None
    try:
        if not os.path.exists(res["LOG_DIR"]):
            os.makedirs(res["LOG_DIR"])
        if not os.path.exists(res["REPORT_DIR"]):
            os.makedirs(res["REPORT_DIR"])
    except:
        logger.exception("Not possible to create path")

    return res


def find_the_newest_file(path_log, path_report):
    """
    Return file to analyze, date (from name) or None
    :param path_log: path to log folder
    :param path_report: path to report folder
    :return: filename and date YYYY.mm.dd
    """
    files = os.listdir(path_log)
    paths = list()
    for basename in files:
        name, ext = os.path.splitext(basename)
        filename_format = \
            re.compile(r"""(\bnginx-access-ui\.log-\d{8}(\.[a-z]{2}$|$))""")
        if (re.search(filename_format, basename) and
                ((ext == ".gz") or (re.search(r"""\.log-\d{8}$""", ext)))):
            paths.append(os.path.join(basename))
    if len(paths) > 0:
        def filter_date(path):
            filter = re.compile(r"(.+)log-(?P<filedate>\d{8})")
            filedate_filtered = re.search(filter, path)
            if filedate_filtered:
                datedict = filedate_filtered.groupdict()
                filedate = datedict["filedate"]
            try:
                datetime.datetime.strptime(filedate, '%Y%m%d')
            except ValueError:
                filedate = "00000000"
            return filedate
        filename = os.path.join(
                                path_log,
                                max(
                                    paths,
                                    key=lambda x:
                                    filter_date(x)))
        filedate = filter_date(filename)
        filedate = \
            filter_date(filename)[-8:-4] + \
            '.' + filter_date(filename)[-4:-2] + \
            '.' + filter_date(filename)[-2:]

        report_files = os.listdir(path_report)

        for file in report_files:
            if f"report-{filedate}.html" == file:
                logger.info(f"Last log {filename} "
                             f"had been processed already. "
                             f"Report is here: {path_report, basename}")
                return None, filedate
    else:
        logger.info("No files to analyze")
        return None, None
    return filename, filedate


def __parse_line(pline, purlList: dict):
    """
    Log Line parser
    :param pline: line to parse
    :param purlList: dict of parsed urls {"url": [t1, t2...]}
    :return: updated purlList: dict of parsed urls {"url": [t1, t2...]}
    """
    data = re.search(lineformat, pline)
    if data:
        datadict = data.groupdict()
        request_time = float(datadict["requesttime"])
        url = datadict["url"]
        if url not in purlList.keys():
            purlList[url] = []
        purlList[url].append(request_time)
    else:
        logger.debug(f"Not possible tp parse {pline}")
    return purlList


def process_file(ppath, perrperc):
    """
    Read log line by line and take data from it
    :param perrperc: % errors
    :param ppath: path to open file for analyze
    :return: dict_with_data with all parsed data {"url" : [t1, t2...]}
    """
    try:
        data_to_read = (
            open(ppath, 'rb'),
            gzip.open(ppath, 'rb'))[ppath.endswith('gz')]
        lines = (line.decode("utf-8") for line in data_to_read)
        dict_with_data = dict()
        parsed_data_from_file = (__parse_line(line, dict_with_data)
                                 for line in lines)
        lst = [elem for elem in parsed_data_from_file]
        data_to_read.close()
    except:
        logger.exception(f"Can not read / parse {ppath} correctly")
        return None
    # count percent of errors
    error_perc = 100.0 - (sum(len(v) for v in dict_with_data.values()) /
                          len(lst))*100 if len(lst) > 0 else 100.0
    if int(error_perc) > perrperc:
        logger.info(f"More than {perrperc}% of errors "
                     f"when log data parsing: {error_perc}%. Stop")
        return None
    logger.info(f"Parsing errors %: {error_perc}%")
    return dict_with_data


def __count_statistic(pkey, pvalue, ptotalurls, ptotaltime):
    """
    Count stat by each url
    :param pkey: url
    :param pvalue: list of req.times
    :param ptotalurls: total urls
    :param ptotaltime: total time
    :return: list of data [
                            count of requests,
                            avarage url req.time,
                            max url req.time,
                            sum url req.time,
                            url,
                            median url req.time,
                            time in %,
                            number requests in %
    """
    return [len(pvalue),
            round(sum(t for t in pvalue) / len(pvalue), 3),
            round(max(pvalue), 3),
            round(sum(t for t in pvalue), 3),
            pkey,
            round(sorted(pvalue)[len(pvalue) // 2]
                  if len(pvalue) % 2
                  else sum(sorted(pvalue)[
                           len(pvalue) // 2 - 1:
                           len(pvalue) // 2 + 1]) / 2,
                  3),
            round(sum(t for t in pvalue) * 100 / ptotaltime, 3),
            round(len(pvalue) * 100 / ptotalurls, 3)
            ]


def generate_report(prawdata, preportLines):
    """
    Prepare raw data before rendering
    :param prawdata: dict of data to render
    :param preportLines: from config $REPORT_SIZE
    :return: res_table to set in HTML
    """
    # [{"count": 2767,
    # "time_avg": 62.994999999999997,
    # "time_max": 9843.5689999999995,
    # "time_sum": 174306.35200000001,
    # "url": "/api/v2/internal/html5/phantomjs/queue/?wait=1m",
    # "time_med": 60.073,
    # "time_perc": 9.0429999999999993,
    # "count_perc": 0.106}...]
    table = list()
    cols = ["count", "time_avg", "time_max",
            "time_sum", "url", "time_med",
            "time_perc", "count_perc"]
    count_of_different_urls = len(prawdata)  # total different urls
    count_of_urls = sum(
        len(v) for v in prawdata.values())  # total parsed requests
    request_time_of_all_requests = \
        sum(
            sum(t for t in v)
            for v in prawdata.values())  # total time spent for requests
    for k, v in prawdata.items():
        stat = __count_statistic(
            k, v, count_of_urls, request_time_of_all_requests)
        table.append(dict(zip(cols, stat)))
    res_table = sorted(table,
                       key=lambda x:
                       x['time_sum'])[
                                    -preportLines
                                    if preportLines < len(prawdata)
                                    else -len(prawdata):]
    res_table.reverse()
    return res_table


def render_report(pcfg, pdate, pdata):
    """
    Render data to html report file
    :param pcfg: path to write report
    :param pdate: date of report
    :param pdata: data for report
    :return: path to report file or None
    """
    src_file_path = os.path.join(pcfg, 'report.html')
    dst_file_path = os.path.join(pcfg, f'report-{pdate}.html')
    try:
        with open(src_file_path, 'r', encoding="utf-8") as fsrc:
            with open(dst_file_path, 'w+', encoding="utf-8") as fdst:
                lines = fsrc.read()
                d = dict(table_json=pdata)
                new_lines = Template(lines).safe_substitute(d)
                fdst.write(new_lines)
    except:
        logger.\
            exception("Not possible to create report. Stop")
        return None
    return dst_file_path


def main(pconfig, pcfg, perrperc):
    """
    Define paths to log, report. Find the newest file and parse it.
    Prepare data for report and render it to html file
    :param pconfig: default config (if not use --config)
    :param pcfg: path if --config $PATH else None
    :param perrperc: permissible number of error in log (%)
    :return:
    """
    logger.info(f"{__file__}. Starting work...")
    logger.info(f"Input config parameters: {sys.argv[1:]}\n"
                 f"Define config parameters")
    try:
        cfg = read_config(pconfig, pcfg)
        if cfg is None:
            sys.exit(-3)
        logger.info(f"Use {cfg}")
        # find the newest file in $LOG_DIR
        logger.info("Define a file to analyze")
        the_newest_file, file_date = find_the_newest_file(
            cfg["LOG_DIR"],
            cfg["REPORT_DIR"])
        if the_newest_file:
            logger.info(f"File to analyze: "
                         f"{the_newest_file}. Date of log {file_date}")
            logger.info(f"Process {the_newest_file}. "
                         f"Size: {os.path.getsize(the_newest_file)}. "
                         f"It takes some time")
            raw_data_for_report = process_file(the_newest_file, perrperc)
            if raw_data_for_report is None:
                logger.info("Check format a log file. Bye")
                sys.exit(-2)
            logger.info(f"Process was finished succesfully")
            logger.info(f"Generate data for report. "
                         f"Size of Report should be no more "
                         f"{cfg['REPORT_SIZE']} records")
            # parse file
            table_json = generate_report(
                raw_data_for_report, cfg["REPORT_SIZE"])
            logger.\
                info(f"To render into HTML report: "
                     f"{os.path.join('report-', file_date, '.html')}")
            # render report file
            if render_report(
                    cfg["REPORT_DIR"],
                    file_date, table_json) is None:
                sys.exit(-4)
            logger.\
                info("Finish analyzing and report generation")
        else:
            logger.info("Work finished. No report was generated")
    except (OSError, KeyboardInterrupt):
        logger.exception("Someting goes wrong. Stop process")
        sys.exit(-1)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    cfg = import_config(default_path, sys.argv[1:])
    filename = None
    if (cfg and "log_path" in cfg.__dict__):
        filename = os.path. \
            join(cfg.log_path,
                 f'log_analyzer{datetime.datetime.utcnow().timestamp()}.log')
        handler = logging.FileHandler(filename=filename, mode='w')
    else:
        handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler. \
        setFormatter(fmt=logging.
                     Formatter('[%(asctime)s] %(levelname).1s %(message)s',
                               '%Y.%m.%d %H:%M:%S'))
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)
    main(config, cfg, error_percent)
