import unittest
import logging
from log_analyzer import *
import os
import imp


class LogAnalyzerTest(unittest.TestCase):
    @staticmethod
    def create_files_for_test():
        with open(
                "test_config_ok.txt",
                mode='w+',
                encoding="utf-8") as test_file:
                test_file.write("""config={}\n""")
        with open(
                "test_config_ko.txt",
                mode='w+',
                encoding="utf-8") as test_file:
            test_file.write("""config {}""")
        with open(
                "test_config_full_1.txt",
                mode='w+',
                encoding="utf-8") as test_file:
            test_file.write("""config = {
                                            "REPORT_SIZE": 5,
                                            "REPORT_DIR": ".",
                                            "LOG_DIR": "."
                                            }\rlog_path = "."
                            """)
        with open("test_config_full_2.txt",
                  mode='w+',
                  encoding="utf-8") as test_file:
            test_file.write("""config = {
                                            "REPORT_SIZE": 10,
                                            "REPORT_DIR": "./repdir",
                                            "LOG_DIR": "./logdir"
                                            }\rlog_path = "."
                            """)
        with open("test_config_not_full.txt",
                  mode='w+',
                  encoding="utf-8") as test_file:
            test_file.write("""config = {
                                            "REPORT_SIZE": 15,
                                            #"REPORT_DIR": "./repdir",
                                            #"LOG_DIR": "./logdir"
                                            }\rlog_path = "."
                            """)
        with open("test_config_no_config.txt",
                  mode='w+',
                  encoding="utf-8") as test_file:
            test_file.write("""log_path = "." """)

        if not os.path.exists("./dir_test"):
            os.makedirs("./dir_test")

    def create_path_with_files(self, path):
        with open(f"./dir_test/{path}",
                  mode='w+',
                  encoding="utf-8") as test_file:
            test_file.write(""" """)

    def setUp(self):
        """setUp"""
        logging.info("Start testing\n"
                     "====================")
        LogAnalyzerTest.create_files_for_test()

    def test_import_config(self):
        """testing import_config"""
        logging.info(self.shortDescription())

        print('# if --config option is empty')
        test_path = './test_config_ok.txt'
        test_configIn = ['--config']
        with self.assertRaises(SystemExit) as cm:
            import_config(test_path, test_configIn)
        self.assertEqual(cm.exception.code, -5)

        print('# if config option is default and path doen\'t exist')
        test_configIn = ['--config', 'DEFauLT']
        test_path = '.'
        with self.assertRaises(SystemExit) as cm:
            import_config(test_path, test_configIn)
        self.assertEqual(cm.exception.code, -7)

        print('# if config option is default and bad config file')
        test_path = './test_config_ko.txt'
        with self.assertRaises(SystemExit) as cm:
            import_config(test_path, test_configIn)
        self.assertEqual(cm.exception.code, -6)

        print('# if config option is default and good config file')
        test_path = './test_config_ok.txt'
        self.assertIsNotNone(import_config(test_path, test_configIn))

        print('# if config option is not default and bad path')
        with self.assertRaises(SystemExit) as cm:
            import_config(test_path, '.')
        self.assertEqual(cm.exception.code, -5)

        print('# if --config good path: '
              'use --config value instead of default path')
        test_path_not_def = ['--config', './test_config_full_1.txt']
        test_path_def = './test_config_full_2.txt'
        test_cfg_o = import_config(test_path_def, test_path_not_def)
        self.assertEqual(test_cfg_o.config["REPORT_SIZE"], 5)

        print("# if no config option: "
              "use default config from source (return NONE)")
        test_configIn = []
        self.assertIsNone(import_config(test_path, test_configIn))

    def test_read_config(self):
        """testing read_config"""
        logging.info(self.shortDescription())
        print("# Use default config from source")
        test_config = {
                "REPORT_SIZE": 1000,
                "REPORT_DIR": "./reports",
                "LOG_DIR": "./log"
                }
        self.assertEqual(read_config(test_config, None), test_config)

        print("# Use default config from source + "
              "part from config file")
        test_InConf = imp.\
            load_source("cfg1", './test_config_not_full.txt')
        test_config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./log"
        }
        test_config_o = {
            "REPORT_SIZE": 15,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./log"
        }
        self.\
            assertEqual(read_config(test_config, test_InConf), test_config_o)

        print("# Return NONE when no config parameter inside a file. "
              "Not use default from source. in main sys.exit(-3)")
        test_config_file = imp.\
            load_source("cfg2", "./test_config_no_config.txt")
        self.assertIsNone(read_config(test_config, test_config_file))

    def test_find_log_to_analyze(self):
        """testing find_the_newest_file"""
        path = ['nginx-access-ui.log-20210531.gz',  # good
                'Nnginx-access-ui.log-20210531.gz',  # bad name
                'nginx-access-ui.log-021053.gz',  # bad date
                'nginx-access-ui.log-20211331.gz',  # bad date
                'nginx-access-ui.log-20210731.gz.gz',  # bad ext
                'nginx-access-ui.log-20210531.2gz',  # bad ext
                'nginx-access-ui.log-20210531',  # good
                'nginx-access-ui.log-202105311',  # bad date
                'nginx-access-ui.log-20210601']  # good

        logging.info(self.shortDescription())

        print("# no log found: return None")
        test_path = './dir_test'
        test_res = find_the_newest_file(test_path, test_path)
        self.assertIsNone(test_res[0])  # path
        self.assertIsNone(test_res[1])  # date

        print("# check filter of date")
        for p in path:
            self.create_path_with_files(p)
        test_res = find_the_newest_file(test_path, test_path)
        self.assertIn(test_res[0], os.path.
                      join(test_path, 'nginx-access-ui.log-20210601'))  # path
        self.assertEqual(test_res[1], '2021.06.01')  # date

        print('# report already exists')
        self.create_path_with_files(os.path.
                                    join('report-2021.06.01.html'))
        test_res = find_the_newest_file(test_path, test_path)
        self.assertIsNone(test_res[0])  # path
        self.assertEqual(test_res[1], '2021.06.01')  # date

    def test_process_file(self):
        """testing process_file"""
        logging.info(self.shortDescription())
        with open("./dir_test/test.log-12345678", "wb+") as testf:
            for l in range(98):
                testf.write(
                    b"""1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.1\n""")
            testf.write(
                b"""1.125.81.48 -  - [29/Jun/2017:18:36:09 +0300] "GET / HTTP/1.1" 302 5 "-" "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36" "-" "1498750569-299694853-4707-10309530" "36aa8cfc2c" 0.1\n""")
            testf.write(
                b"""1.202.56.176 -  - [29/Jun/2017:03:59:15 +0300] "0" 400 166 "-" "-" "-" "-" "-" 0.000""")
        print('# Percent of error more than permitted: NONE')
        self.assertIsNone(process_file("./dir_test/test.log-12345678", 0))

        print('# Percent of error less than permitted and data parsed')
        self.assertEqual(
            process_file("./dir_test/test.log-12345678", 1),
            {x: [0.1 for y in range(1 if x == '/' else 98)] for x in
             ['/api/v2/banner/25019354', '/']})  # 1 > 1

    def test_report_generation(self):
        """testing generate_report"""
        logging.info(self.shortDescription())
        print('# Generate report data. REPORT_SIZE < size of url')
        self.assertEqual(
            generate_report({x: [0.1 for y in range(1 if x == '/' else 98)]
                             for x in ['/api/v2/banner/25019354', '/']},
                            1),
            [{'count': 98,
              'time_med': 0.1,
              'time_avg': 0.1,
              'time_sum': 9.8,
              'url': '/api/v2/banner/25019354',
              'time_max': 0.1,
              'count_perc': 98.99,
              'time_perc': 98.99}])

        print('# Generate report data. REPORT_SIZE > size of url')
        self.assertEqual(
            generate_report({x: [0.1 for y in range(1 if x == '/' else 98)]
                             for x in ['/api/v2/banner/25019354', '/']}, 3),
            [{
               'count': 98,
               'time_med': 0.1,
               'time_avg': 0.1,
               'time_sum': 9.8,
               'url': '/api/v2/banner/25019354',
               'time_max': 0.1,
               'count_perc': 98.99,
               'time_perc': 98.99},
             {
               'count': 1,
               'time_med': 0.1,
               'time_avg': 0.1,
               'time_sum': 0.1,
               'url': '/',
               'time_max': 0.1,
               'count_perc': 1.01,
               'time_perc': 1.01}]
             )

    def test_render_report(self):
        """testing render_report"""
        print("File with report creation")
        logging.info(self.shortDescription())
        test_table = [{'count': 98,
                       'time_med': 0.1,
                       'time_avg': 0.1,
                       'time_sum': 9.8,
                       'url': '/api/v2/banner/25019354',
                       'time_max': 0.1,
                       'count_perc': 98.99,
                       'time_perc': 98.99}]
        test_path = './dir_test'
        with open('./dir_test/report.html', 'w+', encoding='utf-8') as f:
            f.write("table_json=$table_json")
        test_date = '01.01.01'
        render_report(test_path, test_date, test_table)
        self.assertTrue(os.path.exists(f'./dir_test/report-{test_date}.html'))

    def tearDown(self):
        """tearDown"""
        logging.info(f"Finish for: {self.shortDescription()}\n"
                     "====================")
        os.remove('./test_config_ok.txt')
        os.remove('./test_config_ko.txt')
        os.remove('./test_config_full_1.txt')
        os.remove('./test_config_full_2.txt')
        os.remove('./test_config_no_config.txt')
        os.remove('./test_config_not_full.txt')
        shutil.rmtree('./dir_test', ignore_errors=False, onerror=None)


if __name__ == "__main__":
    unittest.main()