#!/usr/bin/python
#import astropy.io.fits as pf
from numpy import *
#from scipy import integrate
#from scipy import interpolate as intp
import matplotlib.pyplot as plt 
#import os,datetime
import use
# set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=3, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

#####################################  ######################################
#################################### !! #####################################
d2r = 180./pi


'''
Need: 
Nks; RAs_nu; Decs_nu; sgms_nu; MJDs_nu;
filenms, for bkgd pdf.
'''

# New 10 years of data from IceCube
# '''
for i in range(0): # New data. # First merge the IC86b data.
    filenms = array([
        './data_input/IceCube_data_released/icecube_10year_ps/events/IC86_II_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/events/IC86_III_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/events/IC86_IV_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/events/IC86_V_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/events/IC86_VI_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/events/IC86_VII_exp.csv',
        ]) #!
    tmp0 = loadtxt( filenms[0] )  
    tmp1 = loadtxt( filenms[1] )  
    tmp2 = loadtxt( filenms[2] )  
    tmp3 = loadtxt( filenms[3] )  
    tmp4 = loadtxt( filenms[4] )
    tmp5 = loadtxt( filenms[5] )
    tmp = concatenate( (tmp0, tmp1, tmp2, tmp3, tmp4, tmp5), axis=0 )
    print( tmp.shape )
    savetxt( './data_input/IceCube_data_released/icecube_10year_ps/events/IC86_II2VII_exp_BZ.csv', tmp, fmt='%.9f')
    del(tmp0, tmp1, tmp2, tmp3, tmp4, tmp5, tmp)
    exit()

filenms = array([ #!
    './data_input/IceCube_data_released/icecube_10year_ps/events/uncorrected_probably/IC40_exp.csv',\
    './data_input/IceCube_data_released/icecube_10year_ps/events/uncorrected_probably/IC59_exp.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/events/uncorrected_probably/IC79_exp.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/events/uncorrected_probably/IC86_I_exp.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/events/uncorrected_probably/IC86_II2VII_exp_BZ.csv',
    ]) 
col_MJDs = 0 #!
col_sgms = 2 #!
col_RAs = 3  #!
col_Decs = 4 #!
col_Eproxys = 1 #!

for i in range(0): # for rpdc TXS0506 analysis
    filenms = array([ #!
        'data_input/IceCube_data_released/IceCube_data_from_2008_to_2017_related_to_analysis_of_TXS_0506+056/events_IC40.txt',
        'data_input/IceCube_data_released/IceCube_data_from_2008_to_2017_related_to_analysis_of_TXS_0506+056/events_IC59.txt',
        'data_input/IceCube_data_released/IceCube_data_from_2008_to_2017_related_to_analysis_of_TXS_0506+056/events_IC79.txt',
        'data_input/IceCube_data_released/IceCube_data_from_2008_to_2017_related_to_analysis_of_TXS_0506+056/events_IC86a.txt',
        'data_input/IceCube_data_released/IceCube_data_from_2008_to_2017_related_to_analysis_of_TXS_0506+056/events_IC86b.txt',
        'data_input/IceCube_data_released/IceCube_data_from_2008_to_2017_related_to_analysis_of_TXS_0506+056/events_IC86c.txt'
        ]) 
    col_MJDs = 0 #!
    col_sgms = 3 #!
    col_RAs = 1  #!
    col_Decs = 2 #!
    col_Eproxys = 4 #!

# MJD 1st, log10(E/GeV) 2nd,  AngErr[deg] 3rd,  RA[deg] 4th,  Dec[deg] 5th,  Azimuth[deg] 6th,   Zenith[deg] 7th.
Nmax = 2000000 # just need be considerably larger than the largest N

Nks = zeros( len(filenms) );  Nks = array(Nks, dtype=int) # N_j
RAs_nu = zeros( ( len(filenms), Nmax) ); 
Decs_nu = RAs_nu.copy(); 
sgms_nu = RAs_nu.copy(); 
MJDs_nu = RAs_nu.copy(); 
lgEs_prxy_nu = RAs_nu.copy()

for k in range(len(filenms)):
    Nus = loadtxt( filenms[k] )

    #idx = where( (Nus[:,col_Decs]>-100000.)*(Nus[:,col_Decs]<10000000.) )
    idx = where( (Nus[:,col_Decs]>-87.)*(Nus[:,col_Decs]<87.) ) ###!!!
    #idx = where( Nus[:,col_Decs]<0. )
    Nks[k] = len(idx[0])
    MJDs_nu[k, 0:Nks[k]]      = Nus[:, col_MJDs][idx] 
    sgms_nu[k, 0:Nks[k]]      = Nus[:, col_sgms][idx]/d2r 
    RAs_nu [k, 0:Nks[k]]      = Nus[:, col_RAs][idx]/d2r; 
    Decs_nu[k, 0:Nks[k]]      = Nus[:, col_Decs][idx]/d2r 
    lgEs_prxy_nu[k, 0:Nks[k]] = Nus[:, col_Eproxys][idx]

print('# Number of nus in each sample, and sum:', Nks, Nks.sum() )
MJDs_nu = MJDs_nu[:, 0:Nks.max()]; 
RAs_nu  = RAs_nu [:, 0:Nks.max()]; 
Decs_nu = Decs_nu[:, 0:Nks.max()]
sgms_nu = sgms_nu[:, 0:Nks.max()]
#savetxt('Decs_nu.txt', Decs_nu.T)
lgEs_prxy_nu = lgEs_prxy_nu[:, 0:Nks.max()]

#print('# Randomizing RAs and Decs!!!!!!!!!!!!!!!!!') \
#        # If not randomizing, just comment out the following lines
#        # Also remember to change the bkgd pdf
#RAs_nu  = random.uniform(0, 360, RAs_nu.shape)/d2r
#Decs_nu = arccos( random.uniform(-1, 1, Decs_nu.shape) ) - pi/2.  # from -pi/2 to pi/2  # \



for i in range(0): # Mean and median angular error of the events
    tmp = sgms_nu[where(sgms_nu>0)]*d2r  
    print( len(tmp) ) # 
    print( tmp.mean() )  # all 0.85; south: 0.51
    print( median(tmp) ) # all 0.58; south: 0.33
for i in range(0): # check the events time and uptime
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('linear')
    
    lbls = [
            'IC40',
            'IC59',
            'IC79',
            'IC86_I',
            'IC86_II',
            'IC86_III',
            'IC86_IV',
            'IC86_V',
            'IC86_VI',
            'IC86_VII',
            ]
    
    for i in range(len(Nks)):
        plot = ax.plot(MJDs_nu[ i, 0:Nks[i] ], (i)*ones(Nks[i]),'o',label=r'',lw=1.5,ms=0.3) 
        clr = plot[0].get_color()
        ax.plot( [MJDs_nu[i, 0:Nks[i]].max()]*2, [-100,100],'-',c=clr, label=r''+str(i)+' '+lbls[i], lw=1.,ms=1) 
    
    tmp = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_II_exp.csv').T
    ax.plot( tmp[0], 4*ones(len(tmp[0])),'r|', label=r'',lw=1.,ms=10) 
    ax.plot( tmp[1], 4*ones(len(tmp[0])),'b|', label=r'',lw=1.,ms=10) 
    tmp = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_I_exp.csv').T
    ax.plot( tmp[0], 3*ones(len(tmp[0])),'r|', label=r'',lw=1.,ms=10) 
    ax.plot( tmp[1], 3*ones(len(tmp[0])),'b|', label=r'',lw=1.,ms=10) 
    
    
    uptime_filenms = array([
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC40_exp.csv',\
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC59_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC79_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_I_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_II_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_III_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_IV_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_V_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_VI_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_VII_exp.csv',
        ]) #!
    
    for i in range(len(uptime_filenms)):
        tmp = loadtxt( uptime_filenms[i] ).T
        Tstarts = tmp[0]
        Tends = tmp[1]
        if i == 4 or i == 5 or i == 6 or i == 7:
            dTs = Tends[10:] - Tstarts[10:] 
            Ttot = Tends[-1] - Tstarts[10] \
                    # start at 10 becuase in 4 5 6 there are mixtures of the times.
        else:
            dTs = Tends - Tstarts
            Ttot = Tends[-1] - Tstarts[0]
        print( i, '  ', dTs.sum()/Ttot ) # fraction of uptime/total time
    
        Tbs = sort(array( list(Tstarts-5e-9)+list(Tends+5e-9) ))  # +-5e-9 is to account for the counts might be = the edges of the uptime.
        Nums = histogram( MJDs_nu[i], Tbs )[0]
        # print( Nums.sum(),  Nums[::2].sum() ) # Fraction of nus inside the uptime.
    

    ax.set_xlabel(r"MJD  [ days ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    ax.set_ylabel(r"Meaningless",fontsize=20)
    ax.set_xlim() #use.autoscale_y(ax)
    ax.set_ylim(-50,50)
    ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    plt.grid()#ls='-', lw=0.5)
    plt.show()
    exit()

# '''





# backup

# IC59--IC86b, previous release
'''
filenms = array([
    './data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC79-2010-events.txt',\
            # RA in 3rd col., Dec in 4th, sgm_nu in 2nd, logEpro in 1, same for below
    #'data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/all_events.txt',
    './data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC86-2011-events.txt',
    './data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC86-2012-events.txt',
#    './data_input/IceCube_data_released/IceCube-59__Search_for_point_sources_using_muon_events/IceCube-59__Search_for_point_sources_using_muon_events.txt',\
            # RA in 1, Dec in 0, sgm in 4th col, logEpro in 3
    ]) #!

Nmax = 1000000 # just need be considerably larger than the largest N

Nks = zeros( len(filenms) ); Nks = array(Nks, dtype=int) # N_j
RAs_nu = zeros( ( len(filenms), Nmax) )
Decs_nu = RAs_nu.copy(); sgms_nu = RAs_nu.copy()
#zeniths_nu #MJDs_nu = #Eproxys_nu =

for k in range(len(filenms)):
    Nus = loadtxt( filenms[k] )
    
    if k <= 2:
        idx = where( (Nus[:,4]>-87.)*(Nus[:,4]<87.) )
        Nks[k] = len(idx[0])
        RAs_nu [k, 0:Nks[k]] = Nus[:,3][idx]/d2r; 
        Decs_nu[k, 0:Nks[k]] = Nus[:,4][idx]/d2r
        sgms_nu[k, 0:Nks[k]] = Nus[:,2][idx]/d2r
    
        #print( Nus[:,2].min(), Nus[:,2].max() ) # angular err
        #print( 10**Nus[:,1].min(), 10**Nus[:,1].max() ) # Eproxy
    elif k==3:
        idx = where( (Nus[:,4]>-inf)*(Nus[:,0]<inf) )
        Nks[k] = len(idx[0])
        RAs_nu [k, 0:Nks[k]] = Nus[:,1][idx]/d2r;
        Decs_nu[k, 0:Nks[k]] = Nus[:,0][idx]/d2r
        sgms_nu[k, 0:Nks[k]] = Nus[:,4][idx]/d2r
        #Eproxy_nu[k, 0:Nks[k]] = 10**(Nus[:,3][idx])

print('# Number of nus in each sample:', Nks )
RAs_nu  = RAs_nu[:, 0:Nks.max()]; Decs_nu = Decs_nu[:, 0:Nks.max()]
sgms_nu = sgms_nu[:, 0:Nks.max()]
'''
