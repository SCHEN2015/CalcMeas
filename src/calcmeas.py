#!/usr/bin/env python

'''
Owner:      SHI, Chen
E-mail:     chen.shi@alcatel-lucent.com

History:
            v0.1    2016-03-07    SHI, Chen    init version
            v0.2    2016-03-08    SHI, Chen    demo version, calculate EPAY KPIs
            v0.3    2016-03-08    SHI, Chen    refactory the code, use 'dict' as element for infolists
            v0.3.1  2016-03-29    SHI, Chen    [iss001] fix the "div 0" issue
            v0.4    2016-03-30    SHI, Chen    [fea001] support calculating process CPU usage
            v0.5    2016-03-31    SHI, Chen    [fea002] use PrettyTable for the outputs
            v0.6    2016-04-27    SHI, Chen    [fea003] support displaying overall CPU usage for specified hosts
            v0.7    2017-03-14    SHI, Chen    [fea004] support specialized clients on IO blades
'''

import sys
import re
from prettytable import PrettyTable


host_role_definition = {'pilot' : ('0-0-1', '0-0-9'),
                    'db1' : ('0-0-2', '0-0-10'),    # where the EPAY call routing clients running on. 
                    'db2' : ('0-0-3', '0-0-11', '0-1-2', '0-1-10', '0-1-3', '0-1-11'),
                    'io' : ('0-0-4', '0-0-12')      # where the EPAY notification clients running on.
                    }


SA_SPAMEAS_infolist = []
MS_PROCESS_MEAS_infolist = []
MS_PERF_MEAS_infolist = []


def get_block_info(measlog, num):
    '''this function receives measlog content and the current offset, return:
    1. (begin, end) offsets of the message block. format: (int, int)
    2. the report time of the message block. format: 'YYYY-MM-DD hh:mm'
    3*. the message id of the message block.
    *: not implemented. 
    '''
    
    # get (begin, end) offsets    
    begin = end = num
    while re.search(r'\+\+\+', measlog[begin]) is None:
        begin -= 1
    while re.search(r'\+\+\-', measlog[end]) is None:
        end += 1

    # get report time
    match_result = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', measlog[begin])
    if match_result:
        report_time = match_result.group(1)
    else:
        print 'Error: Failed to get report time of the message block.'
        report_time = '1970-01-01 12:00'

    return (begin, end, report_time)


def analyze_measlog(measlog):
    '''this function receives the measlog content, analyze the following tables:
    1. SA_SPAMEAS
    2. MS_PROCESS_MEAS
    and save the useful information in the lists respectively.
    '''
    
    num = 0
    while num < len(measlog):
        
        # analyze SA_SPAMEAS table
        if re.search(r'Measurements for SA_SPAMEAS table', measlog[num]) is not None:

            # get the information of current block
            begin, end, report_time = get_block_info(measlog, num)

            # get useful information
            num = begin
            while num < end:
                match_result = re.search(r'(\d+)\s+(\S+)\s+(\d+)\s+\d+', measlog[num])
                if match_result:
                    SA_SPAMEAS_info = {}
                    SA_SPAMEAS_info['tps'] = int(match_result.group(3)) / int(match_result.group(1)) 
                    SA_SPAMEAS_info['spa_name'] =  match_result.group(2)
                    SA_SPAMEAS_info['report_time'] = report_time
                    
                    # save the information
                    SA_SPAMEAS_infolist.append(SA_SPAMEAS_info)
                
                num += 1
            else:
                print 'Finished processing [', report_time, '] SA_SPAMEAS table;'
        
        # analyze MS_PROCESS_MEAS table
        if re.search(r'Measurements for MS_PROCESS_MEAS table', measlog[num]) is not None:

            # get the information of current block
            begin, end, report_time = get_block_info(measlog, num)

            # get useful information
            num = begin
            while num < end:
                #299  0-0-9   DIAMCL28I_2                     18.89
                match_result = re.search(r'\d+\s+(\d+-\d+-\d+)\s+(\S+)\s+(\d+\.\d+)', measlog[num])
                if match_result:
                    MS_PROCESS_MEAS_info = {}
                    MS_PROCESS_MEAS_info['host_id'] = match_result.group(1)
                    MS_PROCESS_MEAS_info['process_name'] = match_result.group(2)
                    MS_PROCESS_MEAS_info['cpu_usage'] = match_result.group(3)
                    MS_PROCESS_MEAS_info['report_time'] = report_time
                    
                    # save the information
                    MS_PROCESS_MEAS_infolist.append(MS_PROCESS_MEAS_info)
                
                num += 1
            else:
                print 'Finished processing [', report_time, '] MS_PROCESS_MEAS table;'
        
        
        # analyze MS_PERF_MEAS table
        if re.search(r'Control Computer Performance Measurements for MS_PERF_MEAS table', measlog[num]) is not None:

            # get the information of current block
            begin, end, report_time = get_block_info(measlog, num)

            # get useful information
            num = begin
            while num < end:
                #          299  0-0-2              1             0              0          98
                match_result = re.search(r'\d+\s+(\d+-\d+-\d+)\s+\d+\s+\d+\s+\d+\s+(\d+)', measlog[num])
                if match_result:
                    MS_PERF_MEAS_info = {}
                    MS_PERF_MEAS_info['host_id'] = match_result.group(1)
                    MS_PERF_MEAS_info['overall_cpu_usage'] = 100 - int(match_result.group(2))
                    MS_PERF_MEAS_info['report_time'] = report_time
                    
                    # save the information
                    MS_PERF_MEAS_infolist.append(MS_PERF_MEAS_info)
                
                num += 1
            else:
                print 'Finished processing [', report_time, '] MS_PERF_MEAS table;'
                
                
        # increase line number
        num += 1


    #print SA_SPAMEAS_infolist
    #print MS_PROCESS_MEAS_infolist
    #print MS_PERF_MEAS_infolist

    return



def get_summarized_data(report_list):
    '''this function calculates the total number and sum value for each numeric data in a dict-based list. 
    inputs:
        it takes a dict-based list, thus each tuple in the list should be a dict.
    outputs:
        it returns a dict containing the count and sum value of each numeric data in original dicts.
    '''
    summarized_data = {}
    for item in report_list:
        for key in item.keys():
            if type(item[key]) in (int, float):
                if not summarized_data.has_key(key + '(sum)'):
                    summarized_data[key + '(cnt)'] = 1
                    summarized_data[key + '(sum)'] = item[key]
                else:
                    summarized_data[key + '(cnt)'] += 1
                    summarized_data[key + '(sum)'] += item[key]
    
    return summarized_data


def generate_reports():
    '''this function reads information from infolist then calculate the KPIs and print the report.
    assumption: EPAY call routing clients on "db1", notification clients on "io", all standard clients on other blades.
    ''' 
    
    # generate EPAY KPIs report
    spa_name = ''
    epay_kpi_list = []
    
    # build epay_kpi_list from SA_SPAMEAS_infolist
    for item in SA_SPAMEAS_infolist:
        if item['spa_name'].find('EPAY') == 0:
            spa_name = item['spa_name']
            epay_kpi = {}
            epay_kpi['report_time'] = item['report_time']
            epay_kpi['tps'] = item['tps']
            epay_kpi_list.append(epay_kpi)
    
    # add more KPIs to epay_kpi_list from MS_PROCESS_MEAS_infolist
    for epay_kpi in epay_kpi_list:
        
        std_client_num = std_client_cpu_usage = 0
        cr_spc_client_num = nt_spc_client_num = cr_spc_client_cpu_usage = nt_spc_client_cpu_usage = 0
        for item in MS_PROCESS_MEAS_infolist:
            
            # calculate standard client average CPU usage
            if item['report_time'] == epay_kpi['report_time'] and \
            item['host_id'] not in host_role_definition['db1'] and \
            item['host_id'] not in host_role_definition['io'] and \
            item['process_name'].find(spa_name + '_') == 0:
                std_client_num += 1
                std_client_cpu_usage += float(item['cpu_usage'])
 
            # calculate specialized client (call routing) average CPU usage
            if item['report_time'] == epay_kpi['report_time'] and \
            item['host_id'] in host_role_definition['db1'] and \
            item['process_name'].find(spa_name + '_') == 0:
                cr_spc_client_num += 1
                cr_spc_client_cpu_usage += float(item['cpu_usage'])
                
            # calculate specialized client (notification) average CPU usage
            if item['report_time'] == epay_kpi['report_time'] and \
            item['host_id'] in host_role_definition['io'] and \
            item['process_name'].find(spa_name + '_') == 0:
                nt_spc_client_num += 1
                nt_spc_client_cpu_usage += float(item['cpu_usage'])
                
        # calculate and save the KPIs
        epay_kpi['std_client_num'] = std_client_num
        if std_client_num:
            epay_kpi['std_client_cpu_usage'] = std_client_cpu_usage / std_client_num
            epay_kpi['std_client_call_cost'] = epay_kpi['std_client_cpu_usage'] * 10 * epay_kpi['std_client_num'] / epay_kpi['tps']
        else:
            epay_kpi['std_client_cpu_usage'] = 0
            epay_kpi['std_client_call_cost'] = 0
        
        epay_kpi['cr_spc_client_num'] = cr_spc_client_num
        if cr_spc_client_num:
            epay_kpi['cr_spc_client_cpu_usage'] = cr_spc_client_cpu_usage / cr_spc_client_num
            epay_kpi['cr_spc_client_call_cost'] = epay_kpi['cr_spc_client_cpu_usage'] * 10 * epay_kpi['cr_spc_client_num'] / epay_kpi['tps']
        else:
            epay_kpi['cr_spc_client_cpu_usage'] = 0
            epay_kpi['cr_spc_client_call_cost'] = 0

        epay_kpi['nt_spc_client_num'] = nt_spc_client_num
        if nt_spc_client_num:
            epay_kpi['nt_spc_client_cpu_usage'] = nt_spc_client_cpu_usage / nt_spc_client_num
            epay_kpi['nt_spc_client_call_cost'] = epay_kpi['nt_spc_client_cpu_usage'] * 10 * epay_kpi['nt_spc_client_num'] / epay_kpi['tps']
        else:
            epay_kpi['nt_spc_client_cpu_usage'] = 0
            epay_kpi['nt_spc_client_call_cost'] = 0
            
    # get the summary values for the final line
    summarized_data = get_summarized_data(epay_kpi_list)


    # print output title
    print '\nEPAY SPA KPI report:'

    # setup output table
    ptable = PrettyTable(['No', 'Report Time', 'TPS', 'STD #', 'STD %', 'STD Cost', 'CRT #', 'CRT %', 'CRT Cost', 'NTF #', 'NTF %', 'NTF Cost'])
    
    # add data into table
    count = 0
    for item in epay_kpi_list:
        count += 1
        
        ptable.add_row([count, item['report_time'], item['tps'], \
                        item['std_client_num'], format(item['std_client_cpu_usage'], '.2f'), format(item['std_client_call_cost'], '.2f'), \
                        item['cr_spc_client_num'], format(item['cr_spc_client_cpu_usage'], '.2f'), format(item['cr_spc_client_call_cost'], '.2f'), \
                        item['nt_spc_client_num'], format(item['nt_spc_client_cpu_usage'], '.2f'), format(item['nt_spc_client_call_cost'], '.2f')
                        ])

    ptable.add_row(['--','----------------', '-----', '-----', '------', '--------', '-----', '------', '--------', '-----', '------', '--------'])
    ptable.add_row(['>', 'SUMMARY(AVERAGE)', format(summarized_data['tps(sum)'] / summarized_data['tps(cnt)'], 'd'), \
                    '-', format(summarized_data['std_client_cpu_usage(sum)'] / summarized_data['std_client_cpu_usage(cnt)'], '.2f'), \
                    format(summarized_data['std_client_call_cost(sum)'] / summarized_data['std_client_call_cost(cnt)'], '.2f'), \
                    '-', format(summarized_data['cr_spc_client_cpu_usage(sum)'] / summarized_data['cr_spc_client_cpu_usage(cnt)'], '.2f'), \
                    format(summarized_data['cr_spc_client_call_cost(sum)'] / summarized_data['cr_spc_client_call_cost(cnt)'], '.2f'), \
                    '-', format(summarized_data['nt_spc_client_cpu_usage(sum)'] / summarized_data['nt_spc_client_cpu_usage(cnt)'], '.2f'), \
                    format(summarized_data['nt_spc_client_call_cost(sum)'] / summarized_data['nt_spc_client_call_cost(cnt)'], '.2f'),
                    ])
    
    # format this table
    ptable.align = 'r'

    # print this table
    print ptable

    return


def generate_process_cpu_reports(process_name = 'MHRPROC'):
    '''generate the report for specified process cpu usage.'''
    
    process_cpu_report_list = []
    
    # build up basic structure
    for item in MS_PROCESS_MEAS_infolist:
        if {'report_time' : item['report_time']} not in process_cpu_report_list:
            process_cpu_report_list.append({'report_time' : item['report_time']})
            
    #print process_cpu_report_list
    
    # fill up KPIs
    for process_cpu_report in process_cpu_report_list:
        
        #print "calculate CPU usage for", process_name, "at",  process_cpu_report['report_time']
        
        pilot_cnt = pilot_cpu = 0
        db_cnt = db_cpu = 0
        io_cnt = io_cpu = 0
        app_cnt = app_cpu = 0
        
        # fill up KPIs for each time points
        for item in MS_PROCESS_MEAS_infolist:
            if item['process_name'] == process_name and \
            process_cpu_report['report_time'] == item['report_time']:
            
                # prepare cpu usage values for each role
                if item['host_id'] in host_role_definition['pilot']:
                    pilot_cnt += 1
                    pilot_cpu += float(item['cpu_usage'])
                elif item['host_id'] in host_role_definition['io']:
                    io_cnt += 1
                    io_cpu += float(item['cpu_usage'])
                elif item['host_id'] in (host_role_definition['db1'] + host_role_definition['db2']):
                    db_cnt += 1
                    db_cpu += float(item['cpu_usage'])
                else:
                    app_cnt += 1
                    app_cpu += float(item['cpu_usage'])
        else:
            # calculate the average cpu usage
            process_cpu_report['pilot_cnt'] = pilot_cnt
            process_cpu_report['db_cnt'] = db_cnt
            process_cpu_report['io_cnt'] = io_cnt
            process_cpu_report['app_cnt'] = app_cnt
            
            process_cpu_report['pilot_cpu'] = 0 if pilot_cnt == 0 else pilot_cpu / pilot_cnt
            process_cpu_report['db_cpu'] = 0 if db_cnt == 0 else db_cpu / db_cnt
            process_cpu_report['io_cpu'] = 0 if io_cnt == 0 else io_cpu / io_cnt
            process_cpu_report['app_cpu'] = 0 if app_cnt == 0 else app_cpu / app_cnt

    # get the summary values for the final line
    summarized_data = get_summarized_data(process_cpu_report_list)


    # print output title
    print '\nProcess CPU Usage Report:'

    # setup output table
    ptable = PrettyTable(['No', 'Report Time', 'Process', 'PI #', 'PI %', 'DB #', 'DB %', 'IO #', 'IO %', 'AP #', 'AP %'])
    
    # add data into table
    count = 0
    for item in process_cpu_report_list:
        count += 1
        
        ptable.add_row([count, item['report_time'], process_name, \
                        item['pilot_cnt'], format(item['pilot_cpu'], '.2f'), \
                        item['db_cnt'], format(item['db_cpu'], '.2f'), \
                        item['io_cnt'], format(item['io_cpu'], '.2f'), \
                        item['app_cnt'], format(item['app_cpu'], '.2f')
                        ])

    ptable.add_row(['--','----------------', '-------', '----', '------', '----', '------', '----', '------', '----', '------'])
    ptable.add_row(['>', 'SUMMARY(AVERAGE)', process_name, \
                    '-', format(summarized_data['pilot_cpu(sum)'] / summarized_data['pilot_cpu(cnt)'], '.2f'), \
                    '-', format(summarized_data['db_cpu(sum)'] / summarized_data['db_cpu(cnt)'], '.2f'), \
                    '-', format(summarized_data['io_cpu(sum)'] / summarized_data['io_cpu(cnt)'], '.2f'), \
                    '-', format(summarized_data['app_cpu(sum)'] / summarized_data['app_cpu(cnt)'], '.2f')
                    ])
    
    # format this table
    ptable.align = 'r'

    # print this table
    print ptable

    return
    

def generate_hosts_overall_cpu_reports(*host_ids):
    '''generate the report for specified hosts overall cpu usage.'''
    
    # check criteria
    if host_ids == ():
        print 'def generate_hosts_overall_cpu_reports(*host_ids) ...'
        print 'host_ids should be specified. function returned directly.'
        return
    
    hosts_overall_cpu_reports_list = []
    
    # build up basic structure
    for item in MS_PERF_MEAS_infolist:
        if {'report_time' : item['report_time']} not in hosts_overall_cpu_reports_list:
            hosts_overall_cpu_reports_list.append({'report_time' : item['report_time']})
    
    #print hosts_overall_cpu_reports_list
    
    # fill up KPIs
    for hosts_overall_cpu_reports in hosts_overall_cpu_reports_list:
        
        # fill up KPIs for each time points
        for item in MS_PERF_MEAS_infolist:
            if hosts_overall_cpu_reports['report_time'] == item['report_time']:
                
                # fill up overall cpu usage for each host_id
                for host_id in host_ids:
                    if host_id == item['host_id']:
                        hosts_overall_cpu_reports[host_id] = item['overall_cpu_usage']
                        
    #print hosts_overall_cpu_reports_list

    # print output title
    print '\nHosts Overall CPU Usage Report:'

    # setup output table
    ptable = PrettyTable(['No', 'Report Time'] + list(host_ids))
    
    # add data into table
    count = 0
    for item in hosts_overall_cpu_reports_list:
        count += 1
        
        cpu_usage_list = []
        
        for host_id in host_ids:
            if item.has_key(host_id):
                cpu_usage_list.append(item[host_id])
            else:
                cpu_usage_list.append('N/A')
                
        ptable.add_row([count, item['report_time']] + cpu_usage_list)

    # format this table
    ptable.align = 'r'

    # print this table
    print ptable

    return


def main():
    '''check input parameters, load the meanslog file'''
    
    if len(sys.argv) < 2:
        print 'Usage: calcmeas.py <measlog file>'
        return
    else:
        print "Measurement log file: ", sys.argv[1]
        
        # read measlog file
        f = open(sys.argv[1], 'r')
        measlog = f.readlines()
        f.close()

    # analyze the measurement log
    analyze_measlog(measlog)


    print '\nGenerate Reports\n', '=' * 60

    # generate hosts overall CPU usage
    generate_hosts_overall_cpu_reports('0-0-1', '0-0-9', '0-0-2', '0-0-10', '0-0-5')
    
    # generate EPAY reports
    generate_reports()

    # generate process CPU usage
    generate_process_cpu_reports()
    #generate_process_cpu_reports('asd')
    #generate_process_cpu_reports('APROC')

    
    print '\n', '=' * 60
    print 'Finished!'
    
    return


if __name__ == '__main__':
    main()
