import numpy as np
import pandas as pd
import xlsxwriter
import time
import h5toDF
import xlautofit
import math
from input_configuration import *

def get_total(exp_fac):
    total=pd.Series.sum(exp_fac)
    if total<1:
        total=pd.Series.count(exp_fac)
    return(total)

def weighted_average(df_in,col,weights,grouper):
    if grouper==None:
        df_in[col+'_sp']=df_in[col].multiply(df_in[weights])
        n_out=pd.Series.sum(df_in[col+'_sp'])/pd.Series.sum(df_in[weights])
        return(n_out)
    else:
        df_in[col+'_sp']=df_in[col].multiply(df_in[weights])
        df_out=df_in.groupby(grouper).sum()
        df_out[col+'_wa']=df_out[col+'_sp'].divide(df_out[weights])
        return(df_out)

def recode_index(df,old_name,new_name):
    df[new_name]=df.index
    df=df.reset_index()
    del df[old_name]
    df=df.set_index(new_name)
    return df

def get_districts(file):
    zone_district=pd.DataFrame.from_csv(file,index_col=None)
    return(zone_district)

def get_differences(df,colname1,colname2,roundto):
    df['Difference']=df[colname1]-df[colname2]
    df['Percent Difference']=pd.Series.round(df['Difference']/df[colname2]*100,1)
    if type(roundto)==list:
        for i in range(len(df['Difference'])):
            df[colname1][i]=round(df[colname1][i],roundto[i])
            df[colname2][i]=round(df[colname2][i],roundto[i])
            df['Difference'][i]=round(df['Difference'][i],roundto[i])
    else:
        for i in range(len(df['Difference'])):
            df[colname1][i]=round(df[colname1][i],roundto)
            df[colname2][i]=round(df[colname2][i],roundto)
            df['Difference'][i]=round(df['Difference'][i],roundto)
    return(df)

def hhmm_to_min(input):
    minmap={}
    for i in range(0,24):
        for j in range(0,60):
            minmap.update({i*100+j:i*60+j})
    if pd.Series.max(input['Trip']['deptm'])>=1440:
        input['Trip']['deptm']=input['Trip']['deptm'].map(minmap)
    if pd.Series.max(input['Trip']['arrtm'])>=1440:
        input['Trip']['arrtm']=input['Trip']['arrtm'].map(minmap)
    if pd.Series.max(input['Trip']['endacttm'])>=1440:
        input['Trip']['endacttm']=input['Trip']['endacttm'].map(minmap)
    if pd.Series.max(input['Tour']['tlvorig'])>=1440:
        input['Tour']['tlvorig']=input['Tour']['tlvorig'].map(minmap)
    if pd.Series.max(input['Tour']['tardest'])>=1440:
        input['Tour']['tardest']=input['Tour']['tardest'].map(minmap)
    if pd.Series.max(input['Tour']['tlvdest'])>=1440:
        input['Tour']['tlvdest']=input['Tour']['tlvdest'].map(minmap)
    if pd.Series.max(input['Tour']['tarorig'])>=1440:
        input['Tour']['tarorig']=input['Tour']['tarorig'].map(minmap)
    return(input)

def min_to_hour(input,base):
    timemap={}
    for i in range(0,24):
        if i+base<24:
            for j in range(0,60):
                if i+base<9:
                    timemap.update({i*60+j:'0'+str(i+base)+'-0'+str(i+base+1)})
                elif i+base==9:
                    timemap.update({i*60+j:'0'+str(i+base)+'-'+str(i+base+1)})
                else:
                    timemap.update({i*60+j:str(i+base)+'-'+str(i+base+1)})
        else:
            for j in range(0,60):
                if i+base-24<9:
                    timemap.update({i*60+j:'0'+str(i+base-24)+'-0'+str(i+base-23)})
                elif i+base-24==9:
                    timemap.update({i*60+j:'0'+str(i+base-24)+'-'+str(i+base-23)})
                else:
                    timemap.update({i*60+j:str(i+base-24)+'-'+str(i+base-23)})
    output=input.map(timemap)
    return output

def random_colors(number_of_colors):
    colorlist=[]
    for i in range(number_of_colors):
        color='#'
        for j in range(3):
            rn=str(hex(int(math.floor(np.random.uniform(0,256)))))
            if len(rn)==3:
                rn=rn[0:2]+'0'+rn[2]
            color=color+rn[2:4]
        colorlist.append(color)
    return(colorlist)

def DayPattern(data1,data2,name1,name2,location):
    start=time.time()
    merge_per_hh_1=pd.merge(data1['Person'],data1['Household'],'outer')
    merge_per_hh_2=pd.merge(data2['Person'],data2['Household'],'outer')
    Person_1_total=get_total(merge_per_hh_1['psexpfac'])
    Person_2_total=get_total(merge_per_hh_2['psexpfac'])

    #Tours per person
    tpp1=pd.Series.sum(data1['Tour']['toexpfac'])/pd.Series.sum(data1['Person']['psexpfac'])
    tpp2=pd.Series.sum(data2['Tour']['toexpfac'])/pd.Series.sum(data2['Person']['psexpfac'])
    tpp=pd.DataFrame(index=['Tours'])
    tpp[name1]=tpp1
    tpp[name2]=tpp2
    tpp=get_differences(tpp,name1,name2,2)

    #Percent of Tours by Purpose
    ptbp1=data1['Tour'].groupby('pdpurp').sum()['toexpfac']/pd.Series.sum(data1['Tour']['toexpfac'])*100
    ptbp2=data2['Tour'].groupby('pdpurp').sum()['toexpfac']/pd.Series.sum(data2['Tour']['toexpfac'])*100
    ptbp=pd.DataFrame()
    ptbp['Percent of Tours ('+name1+')']=ptbp1
    ptbp['Percent of Tours ('+name2+')']=ptbp2
    ptbp=get_differences(ptbp,'Percent of Tours ('+name1+')','Percent of Tours ('+name2+')',1)
    ptbp=recode_index(ptbp,'pdpurp','Tour Purpose')

    #Tours per Person by Purpose
    tpbp1=data1['Tour'].groupby('pdpurp').sum()['toexpfac']/pd.Series.sum(data1['Person']['psexpfac'])
    tpbp2=data2['Tour'].groupby('pdpurp').sum()['toexpfac']/pd.Series.sum(data2['Person']['psexpfac'])
    tpbp=pd.DataFrame()
    tpbp['Tours per Person ('+name1+')']=tpbp1
    tpbp['Tours per Person ('+name2+')']=tpbp2
    tpbp=get_differences(tpbp,'Tours per Person ('+name1+')','Tours per Person ('+name2+')',3)
    tpbp=recode_index(tpbp,'pdpurp','Tour Purpose')

    #Tours per Person by Purpose and Person Type/Number of Stops
    PersonsDay1=pd.merge(data1['Person'],data1['PersonDay'],on=['hhno','pno'])
    PersonsDay2=pd.merge(data2['Person'],data2['PersonDay'],on=['hhno','pno'])
    tpd={}
    stops={}
    for purpose in pd.Series.value_counts(data1['Tour']['pdpurp']).index:
        if purpose=='Work':
            tc='wktours'
            sc='wkstops'
        elif purpose=='Social':
            tc='sotours'
            sc='sostops'
        elif purpose=='School':
            tc='sctours'
            sc='scstops'
        elif purpose=='Escort':
            tc='estours'
            sc='esstops'
        elif purpose=='Personal Business':
            tc='pbtours'
            sc='pbstops'
        elif purpose=='Shop':
            tc='shtours'
            sc='shstops'
        elif purpose=='Meal':
            tc='mltours'
            sc='mlstops'
        toursPersPurp1=weighted_average(PersonsDay1,tc,'psexpfac','pptyp')[tc+'_wa']
        toursPersPurp2=weighted_average(PersonsDay2,tc,'psexpfac','pptyp')[tc+'_wa']
        toursPersPurp=pd.DataFrame.from_items([(name1,toursPersPurp1),(name2,toursPersPurp2)])
        toursPersPurp=get_differences(toursPersPurp,name1,name2,2)
        toursPersPurp=recode_index(toursPersPurp,'pptyp','Person Type')
        tpd.update({purpose:toursPersPurp})
        person_day_hh1=pd.merge(data1['PersonDay'],data1['Household'],on=['hhno'])
        person_day_hh2=pd.merge(data2['PersonDay'],data2['Household'],on=['hhno'])
        no_stops1=pd.Series.sum(person_day_hh1.query(sc+'==0')['pdexpfac'])/pd.Series.sum(person_day_hh1['pdexpfac'])*100
        no_stops2=pd.Series.sum(person_day_hh2.query(sc+'==0')['pdexpfac'])/pd.Series.sum(person_day_hh2['pdexpfac'])*100
        has_stops1=100-no_stops1
        has_stops2=100-no_stops2
        ps=pd.DataFrame() 
        ps['% of Tours ('+name1+')']=[no_stops1,has_stops1]
        ps['% of Tours ('+name2+')']=[no_stops2,has_stops2]
        ps['index']=['0','1+']
        ps=ps.set_index('index')
        ps=get_differences(ps,'% of Tours ('+name1+')','% of Tours ('+name2+')',1)
        ps=recode_index(ps,'index',purpose+' Tours')
        stops.update({purpose:ps})

    #Work-Based Subtour Generation
    #Total trips per person
    atp1=pd.Series.sum(data1['Trip']['trexpfac'])/pd.Series.sum(data1['Person']['psexpfac'])
    atp2=pd.Series.sum(data2['Trip']['trexpfac'])/pd.Series.sum(data2['Person']['psexpfac'])
    atl1=weighted_average(data1['Trip'].query('travdist>0 and travdist<200'),'travdist','trexpfac',None)
    atl2=weighted_average(data2['Trip'].query('travdist>0 and travdist<200'),'travdist','trexpfac',None)
    ttp1=[atp1,atl1]
    ttp2=[atp2,atl2]
    label=['Average Trips Per Person','Average Trip Length']
    ttp=pd.DataFrame.from_items([('',label),(name1,ttp1),(name2,ttp2)])
    ttp=ttp.set_index('')
    ttp=get_differences(ttp,name1,name2,1)

    #Trip Rates by Purpose
    trp1=data1['Trip'].groupby('dpurp').sum()['trexpfac']/Person_1_total
    trp2=data2['Trip'].groupby('dpurp').sum()['trexpfac']/Person_2_total
    trp=pd.DataFrame()
    trp['Trips per Person ('+name1+')']=trp1
    trp['Trips per Person ('+name2+')']=trp2
    trp=get_differences(trp,'Trips per Person ('+name1+')','Trips per Person ('+name2+')',2)
    trp=recode_index(trp,'dpurp','Destination Purpose')

    #Compile file
    writer=pd.ExcelWriter(location+'/DayPatternReport.xlsx',engine='xlsxwriter')
    tpp.to_excel(excel_writer=writer,sheet_name='Daily Activity Pattern',na_rep='NA',startrow=1)
    workbook=writer.book
    worksheet=writer.sheets['Daily Activity Pattern']
    merge_format=workbook.add_format({'align':'center','bold':True,'border':1})
    worksheet.merge_range(0,0,0,4,'Tours Per Person',merge_format)
    worksheet.merge_range(4,0,4,4,'Percent of Tours by Purpose',merge_format)
    ptbp.to_excel(excel_writer=writer,sheet_name='Daily Activity Pattern',na_rep='NA',startrow=5)
    worksheet.merge_range(15,0,15,4,'Tours per Person by Purpose',merge_format)
    tpbp.to_excel(excel_writer=writer,sheet_name='Daily Activity Pattern',na_rep='NA',startrow=15)
    purposes=pd.Series.value_counts(data1['Tour']['pdpurp']).index
    for i in range(len(purposes)):
        tpd[purposes[i]].to_excel(excel_writer=writer,sheet_name='Tours by Purpose',na_rep='NA',startrow=1,startcol=i*6)
        worksheet=writer.sheets['Tours by Purpose']
        worksheet.merge_range(0,6*i,0,6*i+4,purposes[i]+' Tours by Person Type',merge_format)
        worksheet.merge_range(12,6*i,12,6*i+4,'Number of Stops',merge_format)
        stops[purposes[i]].to_excel(excel_writer=writer,sheet_name='Tours by Purpose',na_rep='NA',startrow=13,startcol=i*6)
        if i!=len(purposes):
            worksheet.write(0,6*i+5,' ')
    ttp.to_excel(excel_writer=writer,sheet_name='Work-Based Subtour Generation',na_rep='NA',startrow=1)
    worksheet=writer.sheets['Work-Based Subtour Generation']
    worksheet.merge_range(0,0,0,4,'Total Trips',merge_format)
    worksheet.merge_range(5,0,5,4,'Trip Rates by Purpose',merge_format)
    trp.to_excel(excel_writer=writer,sheet_name='Work-Based Subtour Generation',na_rep='NA',startrow=6)
    writer.save()
    colwidths=xlautofit.getwidths(location+'/DayPatternReport.xlsx')
    colors=['#06192E','#4EAE47']
    writer=pd.ExcelWriter(location+'/DayPatternReport.xlsx',engine='xlsxwriter')
    tpp.to_excel(excel_writer=writer,sheet_name='Daily Activity Pattern',na_rep='NA',startrow=1)
    workbook=writer.book
    worksheet=writer.sheets['Daily Activity Pattern']
    merge_format=workbook.add_format({'align':'center','bold':True,'border':1})
    worksheet.merge_range(0,0,0,4,'Tours Per Person',merge_format)
    worksheet.merge_range(4,0,4,4,'Percent of Tours by Purpose',merge_format)
    ptbp.to_excel(excel_writer=writer,sheet_name='Daily Activity Pattern',na_rep='NA',startrow=5)
    worksheet.merge_range(15,0,15,4,'Percent of Tours by Purpose',merge_format)
    tpbp.to_excel(excel_writer=writer,sheet_name='Daily Activity Pattern',na_rep='NA',startrow=15)
    purposes=pd.Series.value_counts(data1['Tour']['pdpurp']).index
    for i in range(len(purposes)):
        tpd[purposes[i]].to_excel(excel_writer=writer,sheet_name='Tours by Purpose',na_rep='NA',startrow=1,startcol=i*6)
        worksheet=writer.sheets['Tours by Purpose']
        worksheet.merge_range(0,6*i,0,6*i+4,purposes[i]+' Tours by Person Type',merge_format)
        worksheet.merge_range(12,6*i,12,6*i+4,'Number of Stops',merge_format)
        stops[purposes[i]].to_excel(excel_writer=writer,sheet_name='Tours by Purpose',na_rep='NA',startrow=13,startcol=i*6)
        if i!=len(purposes):
            worksheet.write(0,6*i+5,' ')
    ttp.to_excel(excel_writer=writer,sheet_name='Work-Based Subtour Generation',na_rep='NA',startrow=1)
    worksheet=writer.sheets['Work-Based Subtour Generation']
    worksheet.merge_range(0,0,0,4,'Total Trips',merge_format)
    worksheet.merge_range(5,0,5,4,'Trip Rates by Purpose',merge_format)
    trp.to_excel(excel_writer=writer,sheet_name='Work-Based Subtour Generation',na_rep='NA',startrow=6)
    for sheet in writer.sheets:
        worksheet=writer.sheets[sheet]
        for col_num in range(worksheet.dim_colmax+1):
            worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
        if sheet=='Tours by Purpose':
            for i in range(len(purposes)):
                chart=workbook.add_chart({'type':'column'})
                for col_num in range(6*i+1,6*i+3):
                    chart.add_series({'name':[sheet,1,col_num],
                                      'categories':[sheet,3,6*i,10,6*i],
                                      'values':[sheet,3,col_num,10,col_num],
                                      'fill':{'color':colors[col_num%6-1]}})
                    chart.set_legend({'position':'top'})
                    chart.set_size({'x_scale':1.4,'y_scale':1.25})
                worksheet.insert_chart(18,6*i,chart)
        if sheet=='Work-Based Subtour Generation':
            chart=workbook.add_chart({'type':'column'})
            for col_num in range(1,3):
                chart.add_series({'name':[sheet,6,col_num],
                                  'categories':[sheet,8,0,16,0],
                                  'values':[sheet,8,col_num,16,col_num],
                                  'fill':{'color':colors[col_num-1]}})
            chart.set_legend({'position':'top'})
            chart.set_size({'x_scale':2,'y_scale':1.25})
            worksheet.insert_chart(18,0,chart)
    writer.save()
    print('Day Pattern Report successfully compiled in '+str(round(time.time()-start,1))+' seconds')

def DaysimReport(data1,data2,name1,name2,location,districtfile):
    start=time.time()
    merge_per_hh_1=pd.merge(data1['Person'],data1['Household'],'outer')
    merge_per_hh_2=pd.merge(data2['Person'],data2['Household'],'outer')
    label=[]
    value1=[]
    value2=[]
    Person_1_total=get_total(merge_per_hh_1['psexpfac'])
    Person_2_total=get_total(merge_per_hh_2['psexpfac'])
    label.append('Number of People')
    value1.append(int(round(Person_1_total,-3)))
    value2.append(int(round(Person_2_total,-3)))
    Trip_1_total=get_total(data1['Trip']['trexpfac'])
    Trip_2_total=get_total(data2['Trip']['trexpfac'])
    label.append('Number of Trips')
    value1.append(int(round(Trip_1_total,-3)))
    value2.append(int(round(Trip_2_total,-3)))
    Tour_1_total=get_total(data1['Tour']['toexpfac'])
    Tour_2_total=get_total(data2['Tour']['toexpfac'])
    label.append('Number of Tours')
    value1.append(int(round(Tour_1_total,-3)))
    value2.append(int(round(Tour_2_total,-3)))
    tour_ok_1=data1['Tour'].query('tautodist>0 and tautodist<2000')
    tour_ok_2=data2['Tour'].query('tautodist>0 and tautodist<2000')
    trip_ok_1=data1['Trip'].query('travdist>0 and travdist<2000')
    trip_ok_2=data2['Trip'].query('travdist>0 and travdist<2000')

    ##Basic Summaries
    #Total Households, Persons, and Trips
    tp1=pd.Series.sum(data1['Person']['psexpfac'])
    tp2=pd.Series.sum(data2['Person']['psexpfac'])
    th1=pd.Series.sum(data1['Household']['hhexpfac'])
    th2=pd.Series.sum(data2['Household']['hhexpfac'])
    ttr1=pd.Series.sum(trip_ok_1['trexpfac'])
    ttr2=pd.Series.sum(trip_ok_2['trexpfac'])
    ahhs1=tp1/th1
    ahhs2=tp2/th2
    ntr1=ttr1/tp1
    ntr2=ttr2/tp2
    atl1=weighted_average(trip_ok_1,'travdist','trexpfac',None)
    atl2=weighted_average(trip_ok_2,'travdist','trexpfac',None)
    driver_trips1=trip_ok_1.query('dorp=="Driver"')
    driver_trips2=trip_ok_2.query('dorp=="Driver"')
    vmpp1sp=pd.Series.sum(driver_trips1['travdist']*driver_trips1['trexpfac'])
    vmpp2sp=pd.Series.sum(driver_trips2['travdist']*driver_trips2['trexpfac'])
    vmpp1=vmpp1sp/Person_1_total
    vmpp2=vmpp2sp/Person_2_total
    #Work Location
    wrkrs1=merge_per_hh_1.query('pwtyp=="Paid Full-Time Worker" or pwtyp=="Paid Part-Time Worker"')
    wrkrs2=merge_per_hh_2.query('pwtyp=="Paid Full-Time Worker" or pwtyp=="Paid Part-Time Worker"')
    wrkr_1_hzone=pd.merge(wrkrs1,districtfile,left_on='hhtaz',right_on='TAZ')
    wrkr_2_hzone=pd.merge(wrkrs2,districtfile,left_on='hhtaz',right_on='TAZ')
    total_workers_1=pd.Series.count(wrkrs1['psexpfac'])
    total_workers_2=pd.Series.count(wrkrs2['psexpfac'])
    workers_1=wrkr_1_hzone.query('pwpcl!=hhparcel and pwaudist>0 and pwaudist<200')
    workers_2=wrkr_2_hzone.query('pwpcl!=hhparcel and pwaudist>0 and pwaudist<200')
    workers_1['Share']=workers_1['psexpfac']/pd.Series.sum(workers_1['psexpfac'])
    workers_2['Share']=workers_2['psexpfac']/pd.Series.sum(workers_2['psexpfac'])
    workers1_avg_dist=weighted_average(workers_1,'pwaudist','psexpfac',None)
    workers2_avg_dist=weighted_average(workers_2,'pwaudist','psexpfac',None)
    #School Location
    st1=merge_per_hh_1.query('pstyp=="Full-Time Student" or pstyp=="Part-Time Student"')
    st2=merge_per_hh_2.query('pstyp=="Full-Time Student" or pstyp=="Part-Time Student"')
    st_1_hzone=pd.merge(st1,districtfile,'outer',left_on='hhtaz',right_on='TAZ')
    st_2_hzone=pd.merge(st2,districtfile,'outer',left_on='hhtaz',right_on='TAZ')
    total_students_1=pd.Series.count(st1['hhno'])
    total_students_2=pd.Series.count(st2['hhno'])
    students_1=st_1_hzone.query('pspcl!=hhparcel and psaudist>0 and psaudist<200')
    students_2=st_2_hzone.query('pspcl!=hhparcel and psaudist>0 and psaudist<200')
    students_1['Share']=students_1['psexpfac']/pd.Series.sum(students_1['psexpfac'])
    students_2['Share']=students_2['psexpfac']/pd.Series.sum(students_2['psexpfac'])
    students1_avg_dist=weighted_average(students_1,'psaudist','psexpfac',None)
    students2_avg_dist=weighted_average(students_2,'psaudist','psexpfac',None)
    #Glue DataFrame Together
    thp=pd.DataFrame(index=['Total Persons','Total Households','Average Household Size','Average Trips Per Person','Average Trip Length','Vehicle Miles per Person','Average Distance to Work (Non-Home)','Average Distance to School (Non-Home)'])
    thp[name1]=[tp1,th1,ahhs1,ntr1,atl1,vmpp1,workers1_avg_dist,students1_avg_dist]
    thp[name2]=[tp2,th2,ahhs2,ntr2,atl2,vmpp2,workers2_avg_dist,students2_avg_dist]
    thp=get_differences(thp,name1,name2,[-3,-3,1,1,1,1,1,1])

    #Transit Pass Ownership
    ttp1=pd.Series.sum(data1['Person']['ptpass']*data1['Person']['psexpfac'])
    ttp2=pd.Series.sum(data2['Person']['ptpass']*data2['Person']['psexpfac'])
    ppp1=ttp1/Person_1_total
    ppp2=ttp2/Person_2_total
    tpass=pd.DataFrame(index=['Total Passes','Passes per Person'])
    tpass[name1]=[ttp1,ppp1]
    tpass[name2]=[ttp2,ppp2]
    tpass=get_differences(tpass,name1,name2,[-3,3])

    #Auto Ownership
    ao1=data1['Household'].groupby('hhvehs').sum()['hhexpfac']/pd.Series.sum(data1['Household']['hhexpfac'])*100
    for i in range(5,len(ao1)):
        ao1[4]=ao1[4]+ao1[i]
        ao1=ao1.drop([i])
    ao2=data2['Household'].groupby('hhvehs').sum()['hhexpfac']/pd.Series.sum(data2['Household']['hhexpfac'])*100
    for i in range(5,len(ao2)):
        ao2[4]=ao2[4]+ao2[i]
        ao2=ao2.drop([i])
    ao=pd.DataFrame()
    ao['Percent of Households ('+name1+')']=ao1
    ao['Percent of Households ('+name2+')']=ao2
    ao=get_differences(ao,'Percent of Households ('+name1+')','Percent of Households ('+name2+')',1)
    aonewcol=['0','1','2','3','4+']
    ao['Number of Vehicles in Household']=aonewcol
    ao=ao.reset_index()
    del ao['hhvehs']
    ao=ao.set_index('Number of Vehicles in Household')

    #Boardings
    board=pd.DataFrame(index=['Boardings'])
    board['Total Observed Transit Boardings (2011)']=647127
    board['Implied Transit Boardings (Assuming 1.3 Boardings/Trip)']=1.3*pd.Series.sum((data1['Trip'].query('mode=="Transit"'))['trexpfac'])
    board=get_differences(board,'Total Observed Transit Boardings (2011)','Implied Transit Boardings (Assuming 1.3 Boardings/Trip)',0)

    #File Compile
    writer=pd.ExcelWriter(location+'/DaysimReport.xlsx',engine='xlsxwriter')
    thp.to_excel(excel_writer=writer,sheet_name='Basic Summaries',na_rep='NA')
    tpass.to_excel(excel_writer=writer,sheet_name='Transit Pass Ownership',na_rep='NA')
    ao.to_excel(excel_writer=writer,sheet_name='Automobile Ownership',na_rep='NA')

    board.to_excel(excel_writer=writer,sheet_name='Transit Boardings',na_rep='NA')
    writer.save()
    colwidths=xlautofit.getwidths(location+'/DaysimReport.xlsx')
    writer=pd.ExcelWriter(location+'/DaysimReport.xlsx',engine='xlsxwriter')
    thp.to_excel(excel_writer=writer,sheet_name='Basic Summaries',na_rep='NA')
    tpass.to_excel(excel_writer=writer,sheet_name='Transit Pass Ownership',na_rep='NA')
    ao.to_excel(excel_writer=writer,sheet_name='Automobile Ownership',na_rep='NA')
    board.to_excel(excel_writer=writer,sheet_name='Transit Boardings',na_rep='NA')
    workbook=writer.book
    colors=['#4f8a10','#11568c']
    sheet='Basic Summaries'
    worksheet=writer.sheets[sheet]
    for col_num in range(worksheet.dim_colmax+1):
        worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
    worksheet.set_column(0,worksheet.dim_colmax,width=35)
    worksheet.freeze_panes(0,1)
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 0, col_num],
                            'categories':[sheet,3,0,worksheet.dim_rowmax,0],
                            'values':[sheet,3,col_num,worksheet.dim_rowmax,col_num],
                            'fill':{'color':colors[col_num-1]}})
    chart.set_legend({'position':'top'})
    chart.set_size({'x_scale':2,'y_scale':1.75})
    worksheet.insert_chart('B11',chart)
    sheet='Transit Pass Ownership'
    worksheet=writer.sheets[sheet]
    for col_num in range(worksheet.dim_colmax+1):
        worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
    worksheet.set_column(0,worksheet.dim_colmax,width=35)
    worksheet.freeze_panes(0,1)
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 0, col_num],
                            'categories':[sheet,1,0,1,0],
                            'values':[sheet,1,col_num,1,col_num],
                            'fill':{'color':colors[col_num-1]}})
    chart.set_legend({'position':'top'})
    chart.set_size({'x_scale':2,'y_scale':2.25})
    worksheet.insert_chart('B5',chart)
    sheet='Automobile Ownership'
    worksheet=writer.sheets[sheet]
    for col_num in range(worksheet.dim_colmax+1):
        worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
    worksheet.set_column(0,worksheet.dim_colmax,width=35)
    worksheet.freeze_panes(0,1)
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 0, col_num],
                            'categories':[sheet,2,0,worksheet.dim_rowmax,0],
                            'values':[sheet,2,col_num,worksheet.dim_rowmax,col_num],
                            'fill':{'color':colors[col_num-1]}})
    chart.set_title({'name':'Percentage of Households with Number of Automobiles'})
    chart.set_legend({'position':'top'})
    chart.set_size({'x_scale':2,'y_scale':2})
    worksheet.insert_chart('B9',chart)
    sheet='Transit Boardings'
    worksheet=writer.sheets[sheet]
    for col_num in range(worksheet.dim_colmax+1):
        worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
    worksheet.set_column(0,worksheet.dim_colmax,width=35)
    worksheet.freeze_panes(0,1)
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 0, col_num],
                            'categories':[sheet,1,0,worksheet.dim_rowmax,0],
                            'values':[sheet,1,col_num,worksheet.dim_rowmax,col_num],
                            'fill':{'color':colors[col_num-1]}})
    chart.set_legend({'position':'top'})
    chart.set_size({'x_scale':2,'y_scale':2.25})
    worksheet.insert_chart('B4',chart)
    writer.save()
    print('DaySim Report successfully compiled in '+str(round(time.time()-start,1))+' seconds')

def DestChoice(data1,data2,name1,name2,location,districtfile):
    start=time.time()
    Trip_1_total=get_total(data1['Trip']['trexpfac'])
    Trip_2_total=get_total(data2['Trip']['trexpfac'])
    Tour_1_total=get_total(data1['Tour']['toexpfac'])
    Tour_2_total=get_total(data2['Tour']['toexpfac'])
    tour_ok_1=data1['Tour'].query('tautodist>0 and tautodist<200')
    tour_ok_2=data2['Tour'].query('tautodist>0 and tautodist<200')
    trip_ok_1=data1['Trip'].query('travdist>0 and travdist<200')
    trip_ok_2=data2['Trip'].query('travdist>0 and travdist<200')

    #Average distance by tour purpose
    tourtrip1=pd.merge(tour_ok_1,trip_ok_1,on=['hhno','pno','tour','day'])
    tourtrip2=pd.merge(tour_ok_2,trip_ok_2,on=['hhno','pno','tour','day'])
    triptotal1=weighted_average(tourtrip1,'tautodist','toexpfac','pdpurp')
    triptotal2=weighted_average(tourtrip2,'tautodist','toexpfac','pdpurp')
    atl1=pd.DataFrame.from_items([('Average Tour Length ('+name1+')',pd.Series.round(triptotal1['tautodist_wa'],1))])
    #atl1=pd.DataFrame.from_items([('Average Trip Length ('+name1+')',tourtrip1.groupby('pdpurp').mean()['tautodist'])])
    atl2=pd.DataFrame.from_items([('Average Tour Length ('+name2+')',pd.Series.round(triptotal2['tautodist_wa'],1))])
    atl=pd.merge(atl1,atl2,'outer',left_index=True,right_index=True)
    atl['Difference']=pd.Series.round(atl['Average Tour Length ('+name1+')']-atl['Average Tour Length ('+name2+')'],1)
    atl['Percent Difference']=pd.Series.round((atl['Difference'])/atl['Average Tour Length ('+name2+')']*100,1)
    atl=recode_index(atl,'pdpurp','Tour Purpose')

    #Number of trips by tour purpose
    notrips1=tourtrip1.groupby(['hhno','pno','tour','day']).count()['trexpfac']
    notrips2=tourtrip2.groupby(['hhno','pno','tour','day']).count()['trexpfac']
    notrips1=notrips1.reset_index()
    notrips2=notrips2.reset_index()
    notrips1=notrips1.rename(columns={'trexpfac':'notrips'})
    notrips2=notrips2.rename(columns={'trexpfac':'notrips'})
    toursnotrips1=pd.merge(tour_ok_1,notrips1,on=['hhno','pno','tour'])
    toursnotrips2=pd.merge(tour_ok_2,notrips2,on=['hhno','pno','tour'])
    tourtotal1=weighted_average(toursnotrips1,'notrips','toexpfac','pdpurp')
    tourtotal2=weighted_average(toursnotrips2,'notrips','toexpfac','pdpurp')
    ttd=tourtotal1['notrips_wa']-tourtotal2['notrips_wa']
    ttpd=(tourtotal1['notrips_wa']-tourtotal2['notrips_wa'])/tourtotal2['notrips_wa']*100
    nttp1=pd.DataFrame.from_items([('Average Number of Trips per Tour ('+name1+')',pd.Series.round(tourtotal1['notrips_wa'],1))])
    nttp2=pd.DataFrame.from_items([('Average Number of Trips per Tour ('+name2+')',pd.Series.round(tourtotal2['notrips_wa'],1))])
    nttp=pd.merge(nttp1,nttp2,'outer',left_index=True,right_index=True)
    nttp=get_differences(nttp,'Average Number of Trips per Tour ('+name1+')','Average Number of Trips per Tour ('+name2+')',1)
    nttp=recode_index(nttp,'pdpurp','Tour Purpose')

    #Average Distance by Trip Purpose
    atripdist1=weighted_average(trip_ok_1,'travdist','trexpfac','dpurp')
    atripdist2=weighted_average(trip_ok_2,'travdist','trexpfac','dpurp')
    atripdist=pd.DataFrame()
    atripdist['Average Distance ('+name1+')']=pd.Series.round(atripdist1['travdist_wa'],1)
    atripdist['Average Distance ('+name2+')']=pd.Series.round(atripdist2['travdist_wa'],1)
    atripdist['Difference']=atripdist['Average Distance ('+name1+')']-atripdist['Average Distance ('+name2+')']
    atripdist['Percent Difference']=pd.Series.round(atripdist['Difference']/atripdist['Average Distance ('+name2+')']*100,1)
    atripdist=recode_index(atripdist,'dpurp','Trip Purpose')

    #Average Distance by Tour Mode
    triptotalm1=weighted_average(tourtrip1,'tautodist','trexpfac','tmodetp')
    triptotalm2=weighted_average(tourtrip2,'tautodist','trexpfac','tmodetp')
    atlm1=pd.DataFrame.from_items([('Average Trip Length ('+name1+')',pd.Series.round(triptotalm1['tautodist_wa'],1))])
    atlm2=pd.DataFrame.from_items([('Average Trip Length ('+name2+')',pd.Series.round(triptotalm2['tautodist_wa'],1))])
    atlm=pd.merge(atlm1,atlm2,'outer',left_index=True,right_index=True)
    atlm['Difference']=atlm['Average Trip Length ('+name1+')']-atlm['Average Trip Length ('+name2+')']
    atlm['Percent Difference']=pd.Series.round((atlm['Difference']/atlm['Average Trip Length ('+name2+')'])*100,1)
    atlm=recode_index(atlm,'tmodetp','Tour Mode')

    #Number of Trips by Tour Mode
    tourtotalm1=weighted_average(toursnotrips1,'notrips','toexpfac','tmodetp')
    tourtotalm2=weighted_average(toursnotrips2,'notrips','toexpfac','tmodetp')
    ttdm=tourtotalm1['notrips_wa']-tourtotalm2['notrips_wa']
    ttpdm=(tourtotalm1['notrips_wa']-tourtotalm2['notrips_wa'])/tourtotalm2['notrips_wa']*100
    nttpm1=pd.DataFrame.from_items([('Average Number of Trips per Tour ('+name1+')',pd.Series.round(tourtotalm1['notrips_wa'],1))])
    nttpm2=pd.DataFrame.from_items([('Average Number of Trips per Tour ('+name2+')',pd.Series.round(tourtotalm2['notrips_wa'],1))])
    nttpm=pd.merge(nttpm1,nttpm2,'outer',left_index=True,right_index=True)
    nttpm['Difference']=pd.Series.round(ttdm,1)
    nttpm['Percent Difference']=pd.Series.round(ttpdm,1)
    nttpm=recode_index(nttpm,'tmodetp','Tour Mode')

    #Average Distance by Trip Mode
    atripdist1m=weighted_average(trip_ok_1,'travdist','trexpfac','mode')
    atripdist2m=weighted_average(trip_ok_2,'travdist','trexpfac','mode')
    atripdistm=pd.DataFrame()
    atripdistm['Average Distance ('+name1+')']=pd.Series.round(atripdist1m['travdist_wa'],1)
    atripdistm['Average Distance ('+name2+')']=pd.Series.round(atripdist2m['travdist_wa'],1)
    atripdistm['Difference']=atripdistm['Average Distance ('+name1+')']-atripdistm['Average Distance ('+name2+')']
    atripdistm['Percent Difference']=pd.Series.round(atripdistm['Difference']/atripdistm['Average Distance ('+name2+')']*100,1)
    atripdistm=recode_index(atripdistm,'mode','Trip Mode')

    ##Tours and Trips by Destination District
    #Percent of Tours by Destination District
    toursdest1=pd.merge(tour_ok_1,districtfile,'outer',left_on='tdtaz',right_on='TAZ')
    toursdest2=pd.merge(tour_ok_2,districtfile,'outer',left_on='tdtaz',right_on='TAZ')
    dist1=toursdest1.groupby('New DistrictName').sum()['toexpfac']
    dist2=toursdest2.groupby('New DistrictName').sum()['toexpfac']
    tourdestshare1=pd.Series.round(dist1/Tour_1_total*100,1)
    tourdestshare2=pd.Series.round(dist2/Tour_2_total*100,1)
    tourdest=pd.DataFrame()
    tourdest['Percent of Tours ('+name1+')']=tourdestshare1
    tourdest['Percent of Tours ('+name2+')']=tourdestshare2
    tourdest['Difference']=tourdestshare1-tourdestshare2

    #Percent of Trips by Destination District
    tripsdest1=pd.merge(trip_ok_1,districtfile,'outer',left_on='dtaz',right_on='TAZ')
    tripsdest2=pd.merge(trip_ok_2,districtfile,'outer',left_on='dtaz',right_on='TAZ')
    tdist1=tripsdest1.groupby('New DistrictName').sum()['trexpfac']
    tdist2=tripsdest2.groupby('New DistrictName').sum()['trexpfac']
    tripdestshare1=pd.Series.round(tdist1/Trip_1_total*100,1)
    tripdestshare2=pd.Series.round(tdist2/Trip_2_total*100,1)
    tripdest=pd.DataFrame()
    tripdest['Percent of Trips ('+name1+')']=tripdestshare1
    tripdest['Percent of Trips ('+name2+')']=tripdestshare2
    tripdest['Difference']=tripdestshare1-tripdestshare2

    #Compile the file
    writer=pd.ExcelWriter(location+'/DaysimDestChoiceReport.xlsx',engine='xlsxwriter')
    atl.to_excel(excel_writer=writer,sheet_name='Average Dist by Tour Purpose',na_rep='NA',)
    atlm.to_excel(excel_writer=writer,sheet_name='Average Dist by Tour Mode',na_rep='NA')
    nttp.to_excel(excel_writer=writer,sheet_name='Trips per Tour by Tour Purpose',na_rep='NA')
    nttpm.to_excel(excel_writer=writer,sheet_name='Trips per Tour by Tour Mode',na_rep='NA')
    atripdist.to_excel(excel_writer=writer,sheet_name='Average Dist by Trip Purpose',na_rep='NA')
    atripdistm.to_excel(excel_writer=writer,sheet_name='Average Dist by Trip Mode',na_rep='NA')
    tourdest.to_excel(excel_writer=writer,sheet_name='% Tours by Destination District',na_rep='NA')
    tripdest.to_excel(excel_writer=writer,sheet_name='% Trips by Destination District',na_rep='NA')
    writer.save()
    colwidths=xlautofit.getwidths(location+'/DaysimDestChoiceReport.xlsx')
    writer=pd.ExcelWriter(location+'/DaysimDestChoiceReport.xlsx',engine='xlsxwriter')
    atl.to_excel(excel_writer=writer,sheet_name='Average Dist by Tour Purpose',na_rep='NA',)
    atlm.to_excel(excel_writer=writer,sheet_name='Average Dist by Tour Mode',na_rep='NA')
    nttp.to_excel(excel_writer=writer,sheet_name='Trips per Tour by Tour Purpose',na_rep='NA')
    nttpm.to_excel(excel_writer=writer,sheet_name='Trips per Tour by Tour Mode',na_rep='NA')
    atripdist.to_excel(excel_writer=writer,sheet_name='Average Dist by Trip Purpose',na_rep='NA')
    atripdistm.to_excel(excel_writer=writer,sheet_name='Average Dist by Trip Mode',na_rep='NA')
    tourdest.to_excel(excel_writer=writer,sheet_name='% Tours by Destination District',na_rep='NA')
    tripdest.to_excel(excel_writer=writer,sheet_name='% Trips by Destination District',na_rep='NA')
    workbook=writer.book
    colors=['#ed3300','#00529f']
    for sheet in writer.sheets:
        worksheet=writer.sheets[sheet]
        for col_num in range(worksheet.dim_colmax+1):
            worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
        worksheet.set_column(0,worksheet.dim_colmax,width=35)
        worksheet.freeze_panes(0,1)
        chart=workbook.add_chart({'type':'column'})
        for col_num in range(1,3):
            chart.add_series({'name':[sheet, 0, col_num],
                                'categories':[sheet,2,0,worksheet.dim_rowmax,0],
                                'values':[sheet,2,col_num,worksheet.dim_rowmax,col_num],
                                'fill':{'color':colors[col_num-1]}})
        chart.set_legend({'position':'top'})
        chart.set_size({'x_scale':2,'y_scale':1.5})
        worksheet.insert_chart('B15',chart)
    writer.save()
    print('Destination Choice Report successfully compiled in '+str(round(time.time()-start,1))+' seconds')

def ModeChoice(data1,data2,name1,name2,location):
    start=time.time()
    
    #Subsection Vehicle Miles Per Person
    merge_per_hh_1=pd.merge(data1['Person'],data1['Household'],'outer')
    merge_per_hh_2=pd.merge(data2['Person'],data2['Household'],'outer')
    label=[]
    value1=[]
    value2=[]
    Person_1_total=get_total(merge_per_hh_1['psexpfac'])
    Person_2_total=get_total(merge_per_hh_2['psexpfac'])
    label.append('Number of People')
    value1.append(int(round(Person_1_total,-3)))
    value2.append(int(round(Person_2_total,-3)))
    Trip_1_total=get_total(data1['Trip']['trexpfac'])
    Trip_2_total=get_total(data2['Trip']['trexpfac'])
    label.append('Number of Trips')
    value1.append(int(round(Trip_1_total,-3)))
    value2.append(int(round(Trip_2_total,-3)))
    Tour_1_total=get_total(data1['Tour']['toexpfac'])
    Tour_2_total=get_total(data2['Tour']['toexpfac'])
    label.append('Number of Tours')
    value1.append(int(round(Tour_1_total,-3)))
    value2.append(int(round(Tour_2_total,-3)))
    tour_ok_1=data1['Tour'].query('tautodist>0 and tautodist<2000')
    tour_ok_2=data2['Tour'].query('tautodist>0 and tautodist<2000')
    trip_ok_1=data1['Trip'].query('travtime>0 and travtime<2000')
    trip_ok_2=data2['Trip'].query('travtime>0 and travtime<2000')

    vmpp=pd.DataFrame.from_items([('',label),(name1,value1),(name2,value2)])
    vmpp['Difference']=vmpp[name1]-vmpp[name2]
    vmpp['Percent Difference']=pd.Series.round(vmpp['Difference']/vmpp[name2]*100,1)
    vmpp=vmpp.set_index('')

    ##Subsection Tour Summaries

    #Mode Share
    mode1=data1['Tour'].groupby('tmodetp').sum()['toexpfac']
    mode2=data2['Tour'].groupby('tmodetp').sum()['toexpfac']
    modeshare1=pd.Series.round(mode1/Tour_1_total*100,1)
    modeshare2=pd.Series.round(mode2/Tour_2_total*100,1)
    msdf=pd.DataFrame()
    difference=modeshare1-modeshare2
    modeshare1=modeshare1.sort_index()
    msdf[name1+' Share']=modeshare1
    modeshare2=modeshare2.sort_index()
    msdf[name2+' Share']=modeshare2
    msdf=get_differences(msdf,name1+' Share',name2+' Share',0)
    msdf=recode_index(msdf,'tmodetp','Mode')


    #Mode share by purpose
    tourpurpmode1=pd.DataFrame.from_items([('Purpose',data1['Tour']['pdpurp']),('Mode',data1['Tour']['tmodetp']),('Expansion Factor',data1['Tour']['toexpfac'])])
    tourpurpmode2=pd.DataFrame.from_items([('Purpose',data2['Tour']['pdpurp']),('Mode',data2['Tour']['tmodetp']),('Expansion Factor',data2['Tour']['toexpfac'])])
    tourpurp1=tourpurpmode1.groupby('Purpose').sum()['Expansion Factor']
    tourpurp2=tourpurpmode2.groupby('Purpose').sum()['Expansion Factor']
    tpm1=pd.DataFrame({name1+' Share': tourpurpmode1.groupby(['Purpose','Mode']).sum()['Expansion Factor']/tourpurp1*100},dtype='float').reset_index()
    tpm2=pd.DataFrame({name2+' Share': tourpurpmode2.groupby(['Purpose','Mode']).sum()['Expansion Factor']/tourpurp2*100},dtype='float').reset_index()
    tpm=pd.merge(tpm1,tpm2,'outer')
    tpm=tpm.sort(name2+' Share')

    nrows=pd.Series.value_counts(tpm['Purpose'])
    halfcols=pd.Series.value_counts(tpm['Mode'])
    modenames=halfcols.index
    ncols=[]
    for i in range(len(modenames)):
        ncols.append(modenames[i].encode('ascii','replace')+' ('+name1+')')
        ncols.append(modenames[i].encode('ascii','replace')+' ('+name2+')')
    mbpcdf=pd.DataFrame()
    for column in ncols:   
        filler=pd.Series()
        for purpose in nrows.index:
            filler[purpose]=float('Nan')
        mbpcdf[column]=filler

    for i in range(len(tpm['Purpose'])):
        mbpcdf[tpm['Mode'][i]+' ('+name1+')'][tpm['Purpose'][i]]=round(tpm[name1+' Share'][i],0)
        mbpcdf[tpm['Mode'][i]+' ('+name2+')'][tpm['Purpose'][i]]=round(tpm[name2+' Share'][i],0)

    #Trip Mode by Tour Mode
    tourtrip1=pd.merge(data1['Tour'],data1['Trip'],on=['hhno','pno','tour'])
    tourtrip2=pd.merge(data2['Tour'],data2['Trip'],on=['hhno','pno','tour'])
    counts1=pd.DataFrame({name1+' Count':tourtrip1.groupby(['tmodetp','mode']).sum()['trexpfac']})
    counts2=pd.DataFrame({name2+' Count':tourtrip2.groupby(['tmodetp','mode']).sum()['trexpfac']})
    tcounts=pd.merge(counts1,counts2,left_index=True,right_index=True)
    tcounts.reset_index(inplace=True)
    nrows=pd.Series.value_counts(tourtrip2['tmodetp'])
    halfcols=pd.Series.value_counts(tourtrip2['mode'])
    modenames=halfcols.index
    ncols=[]
    for i in range(len(modenames)):
        ncols.append(modenames[i].encode('ascii','replace')+' ('+name1+')')
        ncols.append(modenames[i].encode('ascii','replace')+' ('+name2+')')
    tmbtm=pd.DataFrame()
    for column in ncols:   
        filler=pd.Series()
        for tourmode in nrows.index:
            filler[tourmode]=0
        tmbtm[column]=filler
    for i in range(len(tcounts.index)):
        tmbtm[tcounts['mode'][i]+' ('+name1+')'][tcounts['tmodetp'][i]]=int(round(tcounts[name1+' Count'][i],0))
        tmbtm[tcounts['mode'][i]+' ('+name2+')'][tcounts['tmodetp'][i]]=int(round(tcounts[name2+' Count'][i],0))

    ##Trip Cross-Tabulations

    #Tours by Mode and Travel Time
    df1=data1['Tour']
    df2=data2['Tour']
    df1['atimesp']=df1['tautotime']*df1['toexpfac']
    df1['adistsp']=df1['tautodist']*df1['toexpfac']
    df1['acostsp']=df1['tautocost']*df1['toexpfac']
    df2['atimesp']=df2['tautotime']*df2['toexpfac']
    df2['adistsp']=df2['tautodist']*df2['toexpfac']
    df2['acostsp']=df2['tautocost']*df2['toexpfac']
    tgrouped1=df1.groupby('tmodetp').sum()
    tgrouped2=df2.groupby('tmodetp').sum()
    tgrouped1['matime']=tgrouped1['atimesp']/tgrouped1['toexpfac']
    tgrouped1['madist']=tgrouped1['adistsp']/tgrouped1['toexpfac']
    tgrouped1['macost']=tgrouped1['acostsp']/tgrouped1['toexpfac']
    tgrouped2['matime']=tgrouped2['atimesp']/tgrouped2['toexpfac']
    tgrouped2['madist']=tgrouped2['adistsp']/tgrouped2['toexpfac']
    tgrouped2['macost']=tgrouped2['acostsp']/tgrouped2['toexpfac']
    toursmtt1=pd.DataFrame()
    toursmtt2=pd.DataFrame()
    toursmtt1['Mean Auto Time ('+name1+')']=pd.Series.round(tgrouped1['matime'],2)
    toursmtt2['Mean Auto Time ('+name2+')']=pd.Series.round(tgrouped2['matime'],2)
    toursmtt=pd.merge(toursmtt1,toursmtt2,'outer',left_index=True,right_index=True)
    toursmtt['Mean Auto Distance ('+name1+')']=pd.Series.round(tgrouped1['madist'],2)
    toursmtt['Mean Auto Distance ('+name2+')']=pd.Series.round(tgrouped2['madist'],2)
    toursmtt['Mean Auto Cost ('+name1+')']=pd.Series.round(tgrouped1['macost'],2)
    toursmtt['Mean Auto Cost ('+name2+')']=pd.Series.round(tgrouped2['macost'],2)
    toursmtt=recode_index(toursmtt,'tmodetp','Mode')

    #Trips by Mode and Travel Time
    tripdf1=data1['Trip']
    tripdf2=data2['Trip']
    tripsmtt1=pd.DataFrame()
    tripsmtt2=pd.DataFrame()
    tripm1=tripdf1.groupby('mode').sum()['trexpfac']
    tripm2=tripdf2.groupby('mode').sum()['trexpfac']
    tms1=tripm1/Trip_1_total*100
    tms2=tripm2/Trip_2_total*100
    tripsmtt1['Total Trips ('+name1+')']=pd.Series.round(tripm1,-4)
    tripsmtt2['Total Trips ('+name2+')']=pd.Series.round(tripm2,-4)
    tripsmtt=pd.merge(tripsmtt1,tripsmtt2,'outer',left_index=True,right_index=True)
    tripsmtt['Mode Share ('+name1+')']=pd.Series.round(tms1,1)
    tripsmtt['Mode Share ('+name2+')']=pd.Series.round(tms2,1)
    tripdf1['atimesp']=tripdf1['travtime']*tripdf1['trexpfac']
    tripdf1['adistsp']=tripdf1['travdist']*tripdf1['trexpfac']
    tripdf1['acostsp']=tripdf1['travcost']*tripdf1['trexpfac']
    tripdf2['atimesp']=tripdf2['travtime']*tripdf2['trexpfac']
    tripdf2['adistsp']=tripdf2['travdist']*tripdf2['trexpfac']
    tripdf2['acostsp']=tripdf2['travcost']*tripdf2['trexpfac']
    tripgrouped1=tripdf1.groupby('mode').sum()
    tripgrouped2=tripdf2.groupby('mode').sum()
    tripgrouped1['matime']=tripgrouped1['atimesp']/tripgrouped1['trexpfac']
    tripgrouped1['madist']=tripgrouped1['adistsp']/tripgrouped1['trexpfac']
    tripgrouped1['macost']=tripgrouped1['acostsp']/tripgrouped1['trexpfac']
    tripgrouped2['matime']=tripgrouped2['atimesp']/tripgrouped2['trexpfac']
    tripgrouped2['madist']=tripgrouped2['adistsp']/tripgrouped2['trexpfac']
    tripgrouped2['macost']=tripgrouped2['acostsp']/tripgrouped2['trexpfac']
    tripsmtt['Mean Auto Time ('+name1+')']=pd.Series.round(tripgrouped1['matime'],2)
    tripsmtt['Mean Auto Time ('+name2+')']=pd.Series.round(tripgrouped2['matime'],2)
    tripsmtt['Mean Auto Distance ('+name1+')']=pd.Series.round(tripgrouped1['madist'],2)
    tripsmtt['Mean Auto Distance ('+name2+')']=pd.Series.round(tripgrouped2['madist'],2)
    tripsmtt['Mean Auto Cost ('+name1+')']=pd.Series.round(tripgrouped1['macost'],2)
    tripsmtt['Mean Auto Cost ('+name2+')']=pd.Series.round(tripgrouped2['macost'],2)
    tripsmtt=recode_index(tripsmtt,'mode','Mode')

    #Trip by purpose and travel time
    ttdf1=data1['Trip']
    ttdf2=data2['Trip']
    ttdf1['ttsp']=ttdf1['travtime']*ttdf1['trexpfac']
    ttdf2['ttsp']=ttdf2['travtime']*ttdf2['trexpfac']
    ttdf1['tdsp']=ttdf1['travdist']*ttdf1['trexpfac']
    ttdf2['tdsp']=ttdf2['travdist']*ttdf2['trexpfac']
    tt1im=ttdf1.groupby(['mode','dpurp']).sum()['trexpfac']
    tt2im=ttdf2.groupby(['mode','dpurp']).sum()['trexpfac']
    tt1=pd.DataFrame(tt1im)
    tt2=pd.DataFrame(tt2im)
    ttrips1im=ttdf1.groupby(['mode','dpurp']).sum()
    ttrips2im=ttdf2.groupby(['mode','dpurp']).sum()
    ttrips1=pd.DataFrame(ttrips1im)
    ttrips2=pd.DataFrame(ttrips2im)
    ttrips1['mtt']=pd.Series.round(ttrips1['ttsp']/ttrips1['trexpfac'],1)
    ttrips2['mtt']=pd.Series.round(ttrips2['ttsp']/ttrips2['trexpfac'],1)
    ttrips1['mtd']=pd.Series.round(ttrips1['tdsp']/ttrips1['trexpfac'],1)
    ttrips2['mtd']=pd.Series.round(ttrips2['tdsp']/ttrips2['trexpfac'],1)
    full1=pd.merge(tt1,ttrips1,'outer',left_index=True,right_index=True)
    full2=pd.merge(tt2,ttrips2,'outer',left_index=True,right_index=True)
    full1=full1.reset_index()
    full2=full2.reset_index()
    tptt1=pd.DataFrame.from_items([('Mode',full1['mode']),('Purpose',full1['dpurp']),('Total Trips ('+name1+')',full1['trexpfac_x']),('Mean Time ('+name1+')',full1['mtt']),('Mean Distance ('+name1+')',full1['mtd'])])
    tptt2=pd.DataFrame.from_items([('Mode',full2['mode']),('Purpose',full2['dpurp']),('Total Trips ('+name2+')',full2['trexpfac_x']),('Mean Time ('+name2+')',full2['mtt']),('Mean Distance ('+name2+')',full2['mtd'])])
    tptt=pd.merge(tptt1,tptt2,'outer')
    tptt=tptt.sort_index(axis=1,ascending=False)
    tptt=tptt.set_index(['Mode','Purpose'])

    #Write DataFrames to Excel File
    writer=pd.ExcelWriter(location+'/ModeChoiceReport.xlsx',engine='xlsxwriter')
    vmpp.to_excel(excel_writer=writer,sheet_name='# People, Trips, and Tours',na_rep='NA')
    msdf.to_excel(excel_writer=writer,sheet_name='Mode Share',na_rep='NA')
    mbpcdf.to_excel(excel_writer=writer,sheet_name='Mode Share by Purpose',na_rep='NA')
    tmbtm.to_excel(excel_writer=writer,sheet_name='Trip Mode by Tour Mode',na_rep='NA')
    toursmtt.to_excel(excel_writer=writer,sheet_name='Tours by Mode & Travel Time',na_rep='NA')
    tripsmtt.to_excel(excel_writer=writer,sheet_name='Trips by Mode & Travel Time',na_rep='NA')
    tptt.to_excel(excel_writer=writer,sheet_name='Trips by Purpose & Travel Time',na_rep='NA')
    writer.save()
    colwidths=xlautofit.getwidths(location+'/ModeChoiceReport.xlsx')
    writer=pd.ExcelWriter(location+'/ModeChoiceReport.xlsx',engine='xlsxwriter')
    vmpp.to_excel(excel_writer=writer,sheet_name='# People, Trips, and Tours',na_rep='NA')
    msdf.to_excel(excel_writer=writer,sheet_name='Mode Share',na_rep='NA')
    mbpcdf.to_excel(excel_writer=writer,sheet_name='Mode Share by Purpose',na_rep='NA')
    tmbtm.to_excel(excel_writer=writer,sheet_name='Trip Mode by Tour Mode',na_rep='NA')
    toursmtt.to_excel(excel_writer=writer,sheet_name='Tours by Mode & Travel Time',na_rep='NA')
    tripsmtt.to_excel(excel_writer=writer,sheet_name='Trips by Mode & Travel Time',na_rep='NA')
    tptt.to_excel(excel_writer=writer,sheet_name='Trips by Purpose & Travel Time',na_rep='NA')    
    workbook=writer.book
    colors=['#0c2c56','#005c5c']
    for sheet in writer.sheets:
        worksheet=writer.sheets[sheet]
        for col_num in range(worksheet.dim_colmax+1):
            worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
        worksheet.freeze_panes(0,1)
        if sheet in ['# People, Trips, and Tours','Mode Share']:
            chart=workbook.add_chart({'type':'column'})
            for col_num in range(1,3):
                if sheet=='# People, Trips, and Tours':
                    chart.add_series({'name':[sheet, 0, col_num],
                                        'categories':[sheet,1,0,worksheet.dim_rowmax,0],
                                        'values':[sheet,1,col_num,worksheet.dim_rowmax,col_num],
                                        'fill':{'color':colors[col_num-1]}})
                    chart.set_legend({'position':'top'})
                    chart.set_size({'x_scale':2,'y_scale':1.75})
                else:
                    chart.add_series({'name':[sheet, 0, col_num],
                                        'categories':[sheet,2,0,worksheet.dim_rowmax,0],
                                        'values':[sheet,2,col_num,worksheet.dim_rowmax,col_num],
                                        'fill':{'color':colors[col_num-1]}})
                    chart.set_legend({'position':'top'})
                    chart.set_size({'x_scale':2,'y_scale':1.75})
            worksheet.insert_chart('B12',chart)
    writer.save()
    writer.close()
    print('Mode Choice Report successfully compiled in '+str(round(time.time()-start,1))+' seconds')

def LongTerm(data1,data2,name1,name2,location,districtfile):
    start=time.time()
    tour_ok_1=data1['Tour'].query('tautodist>0 and tautodist<200')
    tour_ok_2=data2['Tour'].query('tautodist>0 and tautodist<200')
    trip_ok_1=data1['Trip'].query('travtime>0 and travtime<200')
    trip_ok_2=data2['Trip'].query('travtime>0 and travtime<200')
    merge_per_hh_1=pd.merge(data1['Person'],data1['Household'],'outer')
    merge_per_hh_2=pd.merge(data2['Person'],data2['Household'],'outer')

    #Total Households and Persons
    th1=pd.Series.sum(data1['Household']['hhexpfac'])
    th2=pd.Series.sum(data2['Household']['hhexpfac'])
    tp1=pd.Series.sum(data1['Person']['psexpfac'])
    tp2=pd.Series.sum(data2['Person']['psexpfac'])
    ahs1=tp1/th1
    ahs2=tp2/th2
    ph=pd.DataFrame(index=['Total Persons','Total Households','Average Household Size'])
    ph[name1]=[tp1,th1,ahs1]
    ph[name2]=[tp2,th2,ahs2]
    ph=get_differences(ph,name1,name2,[-3,-3,1])
    ph['2010 Census']=[3616747,1454695,round(float(3616747)/1454695,1)]

    ##Work and School Location
    #Workers at Home
    wrkrs1=merge_per_hh_1.query('pwtyp=="Paid Full-Time Worker" or pwtyp=="Paid Part-Time Worker"')
    wrkrs2=merge_per_hh_2.query('pwtyp=="Paid Full-Time Worker" or pwtyp=="Paid Part-Time Worker"')
    wkr_1_hzone=pd.merge(districtfile,wrkrs1,left_on='TAZ',right_on='hhtaz')
    wkr_2_hzone=pd.merge(districtfile,wrkrs2,left_on='TAZ',right_on='hhtaz')
    total_workers_1=pd.Series.sum(wrkrs1['psexpfac'])
    total_workers_2=pd.Series.sum(wrkrs2['psexpfac'])
    works_at_home_1=wkr_1_hzone.query('pwpcl==hhparcel')
    works_at_home_2=wkr_2_hzone.query('pwpcl==hhparcel')
    work_home_county_1=works_at_home_1.groupby('County').sum()['psexpfac']
    work_home_county_2=works_at_home_2.groupby('County').sum()['psexpfac']
    work_home_1=pd.Series.sum(work_home_county_1)
    work_home_2=pd.Series.sum(work_home_county_2)
    wh=pd.DataFrame(index=['Total Workers at Home','Total Workers','Share at Home'])
    wh[name1]=[work_home_1,total_workers_1,work_home_1/total_workers_1*100]
    wh[name2]=[work_home_2,total_workers_2,work_home_2/total_workers_2*100]
    wh=get_differences(wh,name1,name2,[-3,-3,1])
    wh['2006-2010 CTPP']=[91615,1805125,5.1]
    #By county
    whbc=pd.DataFrame()
    whbc[name1]=work_home_county_1
    whbc[name2]=work_home_county_2
    whbc=get_differences(whbc,name1,name2,0)
    whbc['2006-2010 CTPP']=[53625,6475,15705,15810]

    #Average Distance to Work in Miles
    workers_1=wkr_1_hzone.query('pwaudist>0 and pwaudist<200 and hhparcel!=pwpcl')
    workers_2=wkr_2_hzone.query('pwaudist>0 and pwaudist<200 and hhparcel!=pwpcl')
    workers_1_ft=workers_1.query('pwtyp=="Paid Full-Time Worker"')
    workers_2_ft=workers_2.query('pwtyp=="Paid Full-Time Worker"')
    workers_1_pt=workers_1.query('pwtyp=="Paid Part-Time Worker"')
    workers_2_pt=workers_2.query('pwtyp=="Paid Part-Time Worker"')
    workers_1_female=workers_1.query('pgend=="Female"')
    workers_2_female=workers_2.query('pgend=="Female"')
    workers_1_male=workers_1.query('pgend=="Male"')
    workers_2_male=workers_2.query('pgend=="Male"')
    workers_1_ageund30=workers_1.query('pagey<30')
    workers_2_ageund30=workers_2.query('pagey<30')
    workers_1_age30to49=workers_1.query('pagey>=30 and pagey<50')
    workers_2_age30to49=workers_2.query('pagey>=30 and pagey<50')
    workers_1_age50to64=workers_1.query('pagey>=50 and pagey<65')
    workers_2_age50to64=workers_2.query('pagey>=50 and pagey<65')
    workers_1_age65up=workers_1.query('pagey>=65')
    workers_2_age65up=workers_2.query('pagey>=65')

    workers_1['Share']=workers_1['psexpfac']/pd.Series.sum(workers_1['psexpfac'])
    workers_2['Share']=workers_2['psexpfac']/pd.Series.sum(workers_2['psexpfac'])
    workers_1_avg_dist=weighted_average(workers_1,'pwaudist','psexpfac',None)
    workers_2_avg_dist=weighted_average(workers_2,'pwaudist','psexpfac',None)
    workers_1_avg_dist_ft=weighted_average(workers_1_ft,'pwaudist','psexpfac',None)
    workers_2_avg_dist_ft=weighted_average(workers_2_ft,'pwaudist','psexpfac',None)
    workers_1_avg_dist_pt=weighted_average(workers_1_pt,'pwaudist','psexpfac',None)
    workers_2_avg_dist_pt=weighted_average(workers_2_pt,'pwaudist','psexpfac',None)
    workers_1_avg_dist_f=weighted_average(workers_1_female,'pwaudist','psexpfac',None)
    workers_2_avg_dist_f=weighted_average(workers_2_female,'pwaudist','psexpfac',None)
    workers_1_avg_dist_m=weighted_average(workers_1_male,'pwaudist','psexpfac',None)
    workers_2_avg_dist_m=weighted_average(workers_2_male,'pwaudist','psexpfac',None)
    workers_1_avg_dist_ageund30=weighted_average(workers_1_ageund30,'pwaudist','psexpfac',None)
    workers_2_avg_dist_ageund30=weighted_average(workers_2_ageund30,'pwaudist','psexpfac',None)
    workers_1_avg_dist_age30to49=weighted_average(workers_1_age30to49,'pwaudist','psexpfac',None)
    workers_2_avg_dist_age30to49=weighted_average(workers_2_age30to49,'pwaudist','psexpfac',None)
    workers_1_avg_dist_age50to64=weighted_average(workers_1_age50to64,'pwaudist','psexpfac',None)
    workers_2_avg_dist_age50to64=weighted_average(workers_2_age50to64,'pwaudist','psexpfac',None)
    workers_1_avg_dist_age65up=weighted_average(workers_1_age65up,'pwaudist','psexpfac',None)
    workers_2_avg_dist_age65up=weighted_average(workers_2_age65up,'pwaudist','psexpfac',None)
    adw=pd.DataFrame(index=['Total','Full-Time','Part-Time','Female','Male','Age Under 30','Age 30-49','Age 50-64','Age Over 65'])
    adw[name1]=[workers_1_avg_dist,workers_1_avg_dist_ft,workers_1_avg_dist_pt,workers_1_avg_dist_f,workers_1_avg_dist_m,workers_1_avg_dist_ageund30,workers_1_avg_dist_age30to49,workers_1_avg_dist_age50to64,workers_1_avg_dist_age65up]
    adw[name2]=[workers_2_avg_dist,workers_2_avg_dist_ft,workers_2_avg_dist_pt,workers_2_avg_dist_f,workers_2_avg_dist_m,workers_2_avg_dist_ageund30,workers_2_avg_dist_age30to49,workers_2_avg_dist_age50to64,workers_2_avg_dist_age65up]
    adw=get_differences(adw,name1,name2,1)

    wrkrslessonemi_1=workers_1.query('pwaudist<=1')
    wrkrslessonemi_2=workers_2.query('pwaudist<=1')
    workers_1_less_one_mi=100*pd.Series.sum(wrkrslessonemi_1['psexpfac'])/pd.Series.sum(workers_1['psexpfac'])
    workers_2_less_one_mi=100*pd.Series.sum(wrkrslessonemi_2['psexpfac'])/pd.Series.sum(workers_2['psexpfac'])
    wrkrsgtrtwentymi_1=workers_1.query('pwaudist>20')
    wrkrsgtrtwentymi_2=workers_2.query('pwaudist>20')
    workers_1_gr_twenty_mi=100*pd.Series.sum(wrkrsgtrtwentymi_1['psexpfac'])/pd.Series.sum(workers_1['psexpfac'])
    workers_2_gr_twenty_mi=100*pd.Series.sum(wrkrsgtrtwentymi_2['psexpfac'])/pd.Series.sum(workers_2['psexpfac'])

    xcl=pd.DataFrame(index=['Share of Non-Home Workers Within 1 Mile to Work','Share of Non-Home Workers More than 20 Miles to Work'])
    xcl[name1]=[workers_1_less_one_mi,workers_1_gr_twenty_mi]
    xcl[name2]=[workers_2_less_one_mi,workers_2_gr_twenty_mi]
    xcl=get_differences(xcl,name1,name2,1)

    #Average Distance to School
    students_1=data1['Person'].query('psaudist>0.05 and psaudist<200')
    students_2=data2['Person'].query('psaudist>0.05 and psaudist<200')
    students_1['share']=students_1['psexpfac']/pd.Series.sum(students_1['psexpfac'])
    students_2['share']=students_2['psexpfac']/pd.Series.sum(students_2['psexpfac'])
    students_1_und5=students_1.query('pagey<5')
    students_2_und5=students_2.query('pagey<5')
    students_1_512=students_1.query('pagey>=5 and pagey<13')
    students_2_512=students_2.query('pagey>=5 and pagey<13')
    students_1_1318=students_1.query('pagey>=13 and pagey<19')
    students_2_1318=students_2.query('pagey>=13 and pagey<19')
    students_1_19p=students_1.query('pagey>=19')
    students_2_19p=students_2.query('pagey>=19')

    students_1_avg_dist=weighted_average(students_1,'psaudist','psexpfac',None)
    students_2_avg_dist=weighted_average(students_2,'psaudist','psexpfac',None)
    students_1_dist_und5=weighted_average(students_1_und5,'psaudist','psexpfac',None)
    students_2_dist_und5=weighted_average(students_2_und5,'psaudist','psexpfac',None)
    students_1_dist_512=weighted_average(students_1_512,'psaudist','psexpfac',None)
    students_2_dist_512=weighted_average(students_2_512,'psaudist','psexpfac',None)
    students_1_dist_1318=weighted_average(students_1_1318,'psaudist','psexpfac',None)
    students_2_dist_1318=weighted_average(students_2_1318,'psaudist','psexpfac',None)
    students_1_dist_19p=weighted_average(students_1_19p,'psaudist','psexpfac',None)
    students_2_dist_19p=weighted_average(students_2_19p,'psaudist','psexpfac',None)

    ads=pd.DataFrame(index=['All','Under 5','5 to 12','13 to 18','Over 19'])
    ads[name1]=[students_1_avg_dist,students_1_dist_und5,students_1_dist_512,students_1_dist_1318,students_1_dist_19p]
    ads[name2]=[students_2_avg_dist,students_2_dist_und5,students_2_dist_512,students_2_dist_1318,students_2_dist_19p]
    ads=get_differences(ads,name1,name2,1)

    ##Transit Pass and Auto Ownership
    #Transit Pass Ownership
    Person_1_total=pd.Series.sum(data1['Person']['psexpfac'])
    Person_2_total=pd.Series.sum(data2['Person']['psexpfac'])
    ttp1=pd.Series.sum(data1['Person']['ptpass']*data1['Person']['psexpfac'])
    ttp2=pd.Series.sum(data2['Person']['ptpass']*data2['Person']['psexpfac'])
    ppp1=ttp1/Person_1_total
    ppp2=ttp2/Person_2_total
    tpass=pd.DataFrame(index=['Total Transit Passes','Transit Passes per Person'])
    tpass[name1]=[ttp1,ppp1]
    tpass[name2]=[ttp2,ppp2]
    tpass=get_differences(tpass,name1,name2,[-3,3])

    #Auto Ownership
    ao1=data1['Household'].groupby('hhvehs').sum()['hhexpfac']/pd.Series.sum(data1['Household']['hhexpfac'])*100
    for i in range(5,len(ao1)):
        ao1[4]=ao1[4]+ao1[i]
        ao1=ao1.drop([i])
    ao2=data2['Household'].groupby('hhvehs').sum()['hhexpfac']/pd.Series.sum(data2['Household']['hhexpfac'])*100
    for i in range(5,len(ao2)):
        ao2[4]=ao2[4]+ao2[i]
        ao2=ao2.drop([i])
    ao=pd.DataFrame()
    ao['Percent of Households ('+name1+')']=ao1
    ao['Percent of Households ('+name2+')']=ao2
    ao=get_differences(ao,'Percent of Households ('+name1+')','Percent of Households ('+name2+')',1)
    aonewcol=['0','1','2','3','4+']
    ao['Number of Vehicles in Household']=aonewcol
    ao=ao.reset_index()
    del ao['hhvehs']
    ao=ao.set_index('Number of Vehicles in Household')

    #Share households by auto ownership
    hh_taz1=pd.merge(districtfile,data1['Household'],left_on='TAZ',right_on='hhtaz')
    hh_taz2=pd.merge(districtfile,data2['Household'],left_on='TAZ',right_on='hhtaz')
    aoc1=hh_taz1.groupby(['County','hhvehs']).sum()['hhexpfac']
    aoc2=hh_taz2.groupby(['County','hhvehs']).sum()['hhexpfac']
    counties=[]
    for i in range(len(aoc1.index)):
        if aoc1.index[i][0] not in counties:
            counties.append(aoc1.index[i][0])
    aoc=pd.DataFrame(columns=['0 Cars ('+name1+')','0 Cars ('+name2+')','1 Car ('+name1+')','1 Car ('+name2+')','2 Cars ('+name1+')','2 Cars ('+name2+')','3 Cars ('+name1+')','3 Cars ('+name2+')','4+ Cars ('+name1+')','4+ Cars ('+name2+')'],index=counties)
    aoc=aoc.fillna(float(0))
    for i in range(len(aoc1.index)):
        aoc1[i]=aoc1[i]*100/hh_taz1.groupby('County').sum().query('County=="'+aoc1.index[i][0]+'"')['hhexpfac']
        if aoc1.index[i][1]==0:
            aoc['0 Cars ('+name1+')'][aoc1.index[i][0]]=round(aoc1[i],1)
        elif aoc1.index[i][1]==1:
            aoc['1 Car ('+name1+')'][aoc1.index[i][0]]=round(aoc1[i],1)
        elif aoc1.index[i][1]==2:
            aoc['2 Cars ('+name1+')'][aoc1.index[i][0]]=round(aoc1[i],1)
        elif aoc1.index[i][1]==3:
            aoc['3 Cars ('+name1+')'][aoc1.index[i][0]]=round(aoc1[i],1)
        else:
            aoc['4+ Cars ('+name1+')'][aoc1.index[i][0]]=aoc['4+ Cars ('+name1+')'][aoc1.index[i][0]]+round(aoc1[i],1)
    for i in range(len(aoc2.index)):
        aoc2[i]=aoc2[i]*100/hh_taz2.groupby('County').sum().query('County=="'+aoc2.index[i][0]+'"')['hhexpfac']
        if aoc2.index[i][1]==0:
            aoc['0 Cars ('+name2+')'][aoc2.index[i][0]]=round(aoc2[i],1)
        elif aoc2.index[i][1]==1:
            aoc['1 Car ('+name2+')'][aoc2.index[i][0]]=round(aoc2[i],1)
        elif aoc2.index[i][1]==2:
            aoc['2 Cars ('+name2+')'][aoc2.index[i][0]]=round(aoc2[i],1)
        elif aoc2.index[i][1]==3:
            aoc['3 Cars ('+name2+')'][aoc2.index[i][0]]=round(aoc2[i],1)
        else:
            aoc['4+ Cars ('+name2+')'][aoc2.index[i][0]]=aoc['4+ Cars ('+name1+')'][aoc2.index[i][0]]+round(aoc2[i],1)

    #Households by income group by auto ownership
    incmap={}
    for i in range(0,20000):
        incmap.update({i:'Less than $20,000'})
    for i in range(20000,40000):
        incmap.update({i:'$20,000-$39,999'})
    for i in range(40000,60000):
        incmap.update({i:'$40,000-$59,999'})
    for i in range(60000,75000):
        incmap.update({i:'$60,000-$74,999'})
    for i in range(75000,max([int(pd.Series.max(data1['Household']['hhincome'])),int(pd.Series.max(data2['Household']['hhincome']))])+1):
        incmap.update({i:'More than $75,000'})
    data1['Household']['recinc']=data1['Household']['hhincome'].map(incmap)
    data2['Household']['recinc']=data2['Household']['hhincome'].map(incmap)
    aoi1=data1['Household'].groupby(['recinc','hhvehs']).sum()['hhexpfac']
    aoi2=data2['Household'].groupby(['recinc','hhvehs']).sum()['hhexpfac']
    aoi=pd.DataFrame(columns=['0 Cars ('+name1+')','0 Cars ('+name2+')','1 Car ('+name1+')','1 Car ('+name2+')','2 Cars ('+name1+')','2 Cars ('+name2+')','3 Cars ('+name1+')','3 Cars ('+name2+')','4+ Cars ('+name1+')','4+ Cars ('+name2+')'],index=['Less than $20,000','$20,000-$39,999','$40,000-$59,999','$60,000-$74,999','More than $75,000'])
    aoi=aoi.fillna(float(0))
    for i in range(len(aoi1.index)):
        aoi1[i]=aoi1[i]*100/data1['Household'].groupby('recinc').sum().query('recinc=="'+aoi1.index[i][0]+'"')['hhexpfac']
        if aoi1.index[i][1]==0:
            aoi['0 Cars ('+name1+')'][aoi1.index[i][0]]=round(aoi1[i],1)
        elif aoi1.index[i][1]==1:
            aoi['1 Car ('+name1+')'][aoi1.index[i][0]]=round(aoi1[i],1)
        elif aoi1.index[i][1]==2:
            aoi['2 Cars ('+name1+')'][aoi1.index[i][0]]=round(aoi1[i],1)
        elif aoi1.index[i][1]==3:
            aoi['3 Cars ('+name1+')'][aoi1.index[i][0]]=round(aoi1[i],1)
        else:
            aoi['4+ Cars ('+name1+')'][aoi1.index[i][0]]=aoi['4+ Cars ('+name1+')'][aoi1.index[i][0]]+round(aoi1[i],1)
    for i in range(len(aoi2.index)):
        aoi2[i]=aoi2[i]*100/data2['Household'].groupby('recinc').sum().query('recinc=="'+aoi2.index[i][0]+'"')['hhexpfac']
        if aoi2.index[i][1]==0:
            aoi['0 Cars ('+name2+')'][aoi2.index[i][0]]=round(aoi2[i],1)
        elif aoi2.index[i][1]==1:
            aoi['1 Car ('+name2+')'][aoi2.index[i][0]]=round(aoi2[i],1)
        elif aoi2.index[i][1]==2:
            aoi['2 Cars ('+name2+')'][aoi2.index[i][0]]=round(aoi2[i],1)
        elif aoi2.index[i][1]==3:
            aoi['3 Cars ('+name2+')'][aoi2.index[i][0]]=round(aoi2[i],1)
        else:
            aoi['4+ Cars ('+name2+')'][aoi2.index[i][0]]=aoi['4+ Cars ('+name1+')'][aoi2.index[i][0]]+round(aoi2[i],1)


    #Compile file
    writer=pd.ExcelWriter(location+'/LongTermReport.xlsx',engine='xlsxwriter')
    ph.to_excel(excel_writer=writer,sheet_name='Basic Summaries',na_rep='NA',startrow=1)
    workbook=writer.book
    worksheet=writer.sheets['Basic Summaries']
    merge_format=workbook.add_format({'align':'center','bold':True,'border':1})
    worksheet.merge_range(0,0,0,5,'Total Households and Persons',merge_format)
    wh.to_excel(excel_writer=writer,sheet_name='Workers at Home',na_rep='NA')
    worksheet=writer.sheets['Workers at Home']
    worksheet.merge_range(5,0,5,5,' ',merge_format)
    whbc.to_excel(excel_writer=writer,sheet_name='Workers at Home',na_rep='NA',startrow=6)
    adw.to_excel(excel_writer=writer,sheet_name='Avg Dist to Work and School',na_rep='NA',startrow=1)
    worksheet=writer.sheets['Avg Dist to Work and School']
    worksheet.merge_range(0,0,0,4,' ',merge_format)
    xcl.to_excel(excel_writer=writer,sheet_name='Avg Dist to Work and School',na_rep='NA',startrow=12)
    worksheet.merge_range(0,6,0,10,' ',merge_format)
    worksheet.write(0,5,' ')
    ads.to_excel(excel_writer=writer,sheet_name='Avg Dist to Work and School',na_rep='NA',startrow=1,startcol=6)
    tpass.to_excel(excel_writer=writer,sheet_name='Transit Pass and Auto Ownership',na_rep='NA')
    worksheet=writer.sheets['Transit Pass and Auto Ownership']
    ao.to_excel(excel_writer=writer,sheet_name='Transit Pass and Auto Ownership',na_rep='NA',startrow=4)
    aoc.to_excel(excel_writer=writer,sheet_name='Transit Pass and Auto Ownership',na_rep='NA',startrow=12)
    worksheet.write(12,0,'County',merge_format)
    aoi.to_excel(excel_writer=writer,sheet_name='Transit Pass and Auto Ownership',na_rep='NA',startrow=18)
    worksheet.write(18,0,'Household Income',merge_format)
    writer.save()
    colwidths=xlautofit.getwidths(location+'/LongTermReport.xlsx')
    colors=['#39275B','#C79900']
    writer=pd.ExcelWriter(location+'/LongTermReport.xlsx',engine='xlsxwriter')
    ph.to_excel(excel_writer=writer,sheet_name='Basic Summaries',na_rep='NA',startrow=1)
    workbook=writer.book
    worksheet=writer.sheets['Basic Summaries']
    merge_format=workbook.add_format({'align':'center','bold':True,'border':1})
    worksheet.merge_range(0,0,0,5,'Total Households and Persons',merge_format)
    wh.to_excel(excel_writer=writer,sheet_name='Workers at Home',na_rep='NA')
    worksheet=writer.sheets['Workers at Home']
    worksheet.merge_range(5,0,5,5, 'Workers at Home by County',merge_format)
    whbc.to_excel(excel_writer=writer,sheet_name='Workers at Home',na_rep='NA',startrow=6)
    chart=workbook.add_chart({'type':'column'})
    sheet='Workers at Home'
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 6, col_num],
                          'categories':[sheet,8,0,11,0],
                          'values':[sheet,8,col_num,11,col_num],
                          'fill':{'color':colors[col_num-1]}})
    chart.add_series({'name':[sheet,6,5],
                      'categories':[sheet,8,0,11,0],
                      'values':[sheet,8,5,11,5],
                      'fill':{'color':'#000000'}})
    chart.set_legend({'position':'top'})
    chart.set_x_axis({'name':'County'})
    chart.set_y_axis({'name':'Number of Home Workers'})
    worksheet.insert_chart('A14',chart)
    adw.to_excel(excel_writer=writer,sheet_name='Avg Dist to Work and School',na_rep='NA',startrow=1)
    worksheet=writer.sheets['Avg Dist to Work and School']
    worksheet.merge_range(0,0,0,4,'Average Distance to Work for Non-Home Workers (Miles)',merge_format)
    xcl.to_excel(excel_writer=writer,sheet_name='Avg Dist to Work and School',na_rep='NA',startrow=12)
    worksheet.merge_range(0,6,0,10,'Average Distance to School (Miles)',merge_format)
    worksheet.write(0,5,' ')
    ads.to_excel(excel_writer=writer,sheet_name='Avg Dist to Work and School',na_rep='NA',startrow=1,startcol=6)
    sheet='Avg Dist to Work and School'
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 1, col_num],
                          'categories':[sheet,2,0,10,0],
                          'values':[sheet,2,col_num,10,col_num],
                          'fill':{'color':colors[col_num-1]}})
    chart.set_legend({'position':'top'})
    chart.set_y_axis({'name':'Average Distance to Work'})
    worksheet.insert_chart('A17',chart)
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(7,9):
        chart.add_series({'name':[sheet, 1, col_num],
                          'categories':[sheet,2,6,6,6],
                          'values':[sheet,2,col_num,6,col_num],
                          'fill':{'color':colors[col_num-7]}})
    chart.set_legend({'position':'top'})
    chart.set_x_axis({'name':'Age'})
    chart.set_y_axis({'name':'Average Distance to School'})
    worksheet.insert_chart('G17',chart)
    tpass.to_excel(excel_writer=writer,sheet_name='Transit Pass and Auto Ownership',na_rep='NA')
    worksheet=writer.sheets['Transit Pass and Auto Ownership']
    ao.to_excel(excel_writer=writer,sheet_name='Transit Pass and Auto Ownership',na_rep='NA',startrow=4)
    aoc.to_excel(excel_writer=writer,sheet_name='Transit Pass and Auto Ownership',na_rep='NA',startrow=12)
    worksheet.write(12,0,'County',merge_format)
    aoi.to_excel(excel_writer=writer,sheet_name='Transit Pass and Auto Ownership',na_rep='NA',startrow=18)
    worksheet.write(18,0,'Household Income',merge_format)
    worksheet.freeze_panes(0,1)
    for sheet in writer.sheets:
        worksheet=writer.sheets[sheet]
        for col_num in range(worksheet.dim_colmax+1):
            worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
    writer.save()

    print('Long Term Report succesfuly compiled in '+str(round(time.time()-start,1))+' seconds')

def TimeChoice(data1,data2,name1,name2,location,districtfile):
    start=time.time()
    merge_per_hh_1=pd.merge(data1['Person'],data1['Household'],on='hhno')
    merge_per_hh_2=pd.merge(data1['Person'],data2['Household'],on='hhno')
    person_1_total=get_total(merge_per_hh_1['psexpfac'])
    person_2_total=get_total(merge_per_hh_2['psexpfac'])
    trip_ok_1=data1['Trip'].query('travdist>0 and travdist<200')
    trip_ok_2=data2['Trip'].query('travdist>0 and travdist<200')
    trip_ok_1=trip_ok_1.reset_index()
    trip_ok_2=trip_ok_2.reset_index()
    tour_ok_1=data1['Tour'].query('tautodist>0 and tautodist<200')
    tour_ok_2=data2['Tour'].query('tautodist>0 and tautodist<200')
    tour_ok_1=tour_ok_1.reset_index()
    tour_ok_2=tour_ok_2.reset_index()

    #Trip arrival time by hour
    trip_ok_1['hr']=min_to_hour(trip_ok_1['arrtm'],3)
    trip_ok_2['hr']=min_to_hour(trip_ok_2['arrtm'],3)
    trip_1_time=trip_ok_1.groupby('hr').sum()['trexpfac']
    trip_2_time=trip_ok_2.groupby('hr').sum()['trexpfac']
    trip_1_time_share=100*trip_1_time/pd.Series.sum(trip_1_time)
    trip_2_time_share=100*trip_2_time/pd.Series.sum(trip_2_time)
    trip_time=pd.DataFrame()
    trip_time[name1]=trip_1_time_share
    trip_time[name2]=trip_2_time_share
    trip_time=get_differences(trip_time,name1,name2,1)
    trip_time=recode_index(trip_time,'hr','Arrival Hour')

    #Tour Primary Destination arrival time by hour
    tour_ok_1['hrapd']=min_to_hour(tour_ok_1['tardest'],3)
    tour_ok_2['hrapd']=min_to_hour(tour_ok_2['tardest'],3)
    tour_1_time_apd=tour_ok_1.groupby('hrapd').sum()['toexpfac']
    tour_2_time_apd=tour_ok_2.groupby('hrapd').sum()['toexpfac']
    tour_1_time_share_apd=100*tour_1_time_apd/pd.Series.sum(tour_1_time_apd)
    tour_2_time_share_apd=100*tour_2_time_apd/pd.Series.sum(tour_2_time_apd)
    tour_time_apd=pd.DataFrame()
    tour_time_apd[name1]=tour_1_time_share_apd
    tour_time_apd[name2]=tour_2_time_share_apd
    tour_time_apd=get_differences(tour_time_apd,name1,name2,1)
    tour_time_apd=recode_index(tour_time_apd,'hrapd','Primary Destination Arrival Hour')

    #Tour Primary Destination Departure time by hour
    tour_ok_1['hrlpd']=min_to_hour(tour_ok_1['tlvdest'],3)
    tour_ok_2['hrlpd']=min_to_hour(tour_ok_2['tlvdest'],3)
    tour_1_time_lpd=tour_ok_1.groupby('hrlpd').sum()['toexpfac']
    tour_2_time_lpd=tour_ok_2.groupby('hrlpd').sum()['toexpfac']
    tour_1_time_share_lpd=100*tour_1_time_lpd/pd.Series.sum(tour_1_time_lpd)
    tour_2_time_share_lpd=100*tour_2_time_lpd/pd.Series.sum(tour_2_time_lpd)
    tour_time_lpd=pd.DataFrame()
    tour_time_lpd[name1]=tour_1_time_share_lpd
    tour_time_lpd[name2]=tour_2_time_share_lpd
    tour_time_lpd=get_differences(tour_time_lpd,name1,name2,1)
    tour_time_lpd=recode_index(tour_time_lpd,'hrlpd','Primary Destination Departure Hour')

    #Compile the file
    writer=pd.ExcelWriter(location+'/TimeChoiceReport.xlsx',engine='xlsxwriter')
    workbook=writer.book
    merge_format=workbook.add_format({'align':'center','bold':True,'border':1})
    trip_time.to_excel(excel_writer=writer,sheet_name='Trip Arrival Times by Hour',na_rep='NA')
    tour_time_apd.to_excel(excel_writer=writer,sheet_name='Tour PD Arr & Dep Times by Hour',na_rep='NA',startrow=1)
    tour_time_lpd.to_excel(excel_writer=writer,sheet_name='Tour PD Arr & Dep Times by Hour',na_rep='NA',startrow=1,startcol=6)
    worksheet=writer.sheets['Tour PD Arr & Dep Times by Hour']
    writer.save()
    colwidths=xlautofit.getwidths(location+'/TimeChoiceReport.xlsx')
    colors=random_colors(6)
    writer=pd.ExcelWriter(location+'/TimeChoiceReport.xlsx',engine='xlsxwriter')
    workbook=writer.book
    merge_format=workbook.add_format({'align':'center','bold':True,'border':1})
    trip_time.to_excel(excel_writer=writer,sheet_name='Trip Arrival Times by Hour',na_rep='NA')
    tour_time_apd.to_excel(excel_writer=writer,sheet_name='Tour PD Arr & Dep Times by Hour',na_rep='NA',startrow=1)
    tour_time_lpd.to_excel(excel_writer=writer,sheet_name='Tour PD Arr & Dep Times by Hour',na_rep='NA',startrow=29)
    sheet='Trip Arrival Times by Hour'
    worksheet=writer.sheets[sheet]
    for col_num in range(worksheet.dim_colmax+1):
        worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
    chart=workbook.add_chart({'type':'column'})
    for colnum in range(1,3):
        chart.add_series({'name':[sheet,0,colnum],
                          'categories':[sheet,2,0,25,0],
                          'values':[sheet,2,colnum,25,colnum],
                          'fill':{'color':colors[colnum-1]},
                          'border':{'color':'black'}})
    chart.set_title({'name':'Trip Arrival Time by Hour of Day'})
    chart.set_size({'width':768,'height':520})
    chart.set_x_axis({'name':'Hour of Day'})
    chart.set_y_axis({'name':'Percent of Trips'})
    chart.set_legend({'position':'top'})
    worksheet.insert_chart('G1',chart)
    sheet='Tour PD Arr & Dep Times by Hour'
    worksheet=writer.sheets[sheet]
    worksheet.merge_range(0,0,0,4,'Tour Share by Primary Destination Arrival Hour',merge_format)
    worksheet.merge_range(28,0,28,4,'Tour Share by Primary Destination Departure Hour',merge_format)
    for col_num in range(worksheet.dim_colmax+1):
        worksheet.set_column(col_num,col_num,colwidths[sheet][col_num])
    chart=workbook.add_chart({'type':'column'})
    for colnum in range(1,3):
        chart.add_series({'name':[sheet,1,colnum],
                          'categories':[sheet,3,0,26,0],
                          'values':[sheet,3,colnum,26,colnum],
                          'fill':{'color':colors[colnum+1]},
                          'border':{'color':'black'}})
    chart.set_title({'name':[sheet,0,0]})
    chart.set_size({'width':640,'height':540})
    chart.set_x_axis({'name':'Hour of Day'})
    chart.set_y_axis({'name':'Percent of Tours'})
    chart.set_legend({'position':'top'})
    worksheet.insert_chart('F1',chart)
    chart=workbook.add_chart({'type':'column'})
    for colnum in range(1,3):
        chart.add_series({'name':[sheet,29,colnum],
                          'categories':[sheet,31,0,54,0],
                          'values':[sheet,31,colnum,54,colnum],
                          'fill':{'color':colors[colnum+3]},
                          'border':{'color':'black'}})
    chart.set_title({'name':[sheet,28,0]})
    chart.set_size({'width':640,'height':540})
    chart.set_x_axis({'name':'Hour of Day'})
    chart.set_y_axis({'name':'Percent of Tours'})
    chart.set_legend({'position':'top'})
    worksheet.insert_chart('F29',chart)
    writer.save()

    print('Time Choice Report successfully compiled in '+str(round(time.time()-start,1))+' seconds')
    
def report_compile(h5_results_file,h5_results_name,
                   h5_comparison_file,h5_comparison_name,
                   guidefile,districtfile,report_output_location):
    print('+-+-+-+Begin summary report file compilation+-+-+-+')
    timerstart=time.time()
    data1 = h5toDF.convert(h5_results_file,guidefile,h5_results_name)
    data2 = h5toDF.convert(h5_comparison_file,guidefile,h5_comparison_name)
    data1=hhmm_to_min(data1)
    data2=hhmm_to_min(data2)
    zone_district = get_districts(districtfile)
    if run_daysim_report == True:
        DaysimReport(data1,data2,h5_results_name,h5_comparison_name,report_output_location,zone_district)
    if run_day_pattern_report == True:
        DayPattern(data1,data2,h5_results_name,h5_comparison_name,report_output_location)
    if run_mode_choice_report == True:
        ModeChoice(data1,data2,h5_results_name,h5_comparison_name,report_output_location)
    if run_dest_choice_report == True:
        DestChoice(data1,data2,h5_results_name,h5_comparison_name,report_output_location,zone_district)
    if run_long_term_report == True:
        LongTerm(data1,data2,h5_results_name,h5_comparison_name,report_output_location,zone_district)
    if run_time_choice_report == True:
        TimeChoice(data1,data2,h5_results_name,h5_comparison_name,report_output_location)
    totaltime=time.time()-timerstart
    if int(totaltime)/60==1:
        print('+-+-+-+Summary report compilation complete in 1 minute and '+str(round(totaltime%60,1))+' seconds+-+-+-+')
    else:
        print('+-+-+-+Summary report compilation complete in '+str(int(totaltime)/60)+' minutes and '+str(round(totaltime%60,1))+' seconds+-+-+-+')


def main():
    report_compile(h5_results_file,h5_results_name,
                   h5_comparison_file,h5_comparison_name,
                   guidefile,districtfile,report_output_location)

main()