#!/usr/bin/python
#################################  ##################################
################################ !! #################################
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
import os,datetime
import use
import tqdm
#set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=6, floatmode='maxprec')
d2r = 180./pi


' Bkgd spatial pdf  using sliding window of Dec instead of cosz, Remove later. '
#   This part was initally copied from likelihood_v3.py and modified.
filenms = array([ 
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC40_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC59_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC79_exp.csv', # cdx
    #'./data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC79-2010-events.txt',
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC86_I_exp.csv', # cdx
    #'./data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC86-2011-events.txt',
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC86_II2VII_exp_BZ.csv', # cdx
    ]) #!

bkgd_pdfs = []
Dec_band = 3./d2r
for j in range(0): # Functions for Bkgd spatial pdf
    #
    i = 0; #!
    tmpDecs0 = loadtxt(filenms[i])[:,4]/d2r #!
    def bkgd_pdf_dec0(dec): #!
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-Dec_band; decUL = dec+Dec_band; 
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        print( 1/sqrt( len(where( (tmpDecs0>decLL)*(tmpDecs0<decUL) )[0]) ) )
        return len(where( (tmpDecs0>decLL)*(tmpDecs0<decUL) )[0])/Omega #!
    for i1 in range(0): # get the norm
        def bkgd_pdf0(cos_zenith): #!
            dec = arcsin( -cos_zenith )
            return use.f2a(bkgd_pdf_dec0, dec)  #!
        xx = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000) 
        yy = bkgd_pdf0(xx) #!
        print('# norm of bkgd pdf:', integrate.simps(yy, xx)) 
        exit()
    def bkgd_pdf0a(cos_zenith): #!
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec0, dec)/5864.527224077435/2./pi # for IC 40!
        #return use.f2a(bkgd_pdf_dec0, dec)/17953.24912571124/2./pi # for IC86_II
    
    i = 1; #!
    tmpDecs1 = loadtxt(filenms[i])[:,4]/d2r #!
    def bkgd_pdf_dec1(dec): #!
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-Dec_band; decUL = dec+Dec_band; 
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        print( 1/sqrt( len(where( (tmpDecs1>decLL)*(tmpDecs1<decUL) )[0]) ) )
        return len(where( (tmpDecs1>decLL)*(tmpDecs1<decUL) )[0])/Omega #!
    for i1 in range(0): # get the norm
        def bkgd_pdf1(cos_zenith): #!
            dec = arcsin( -cos_zenith )
            return use.f2a(bkgd_pdf_dec1, dec)  #!
        xx = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000) 
        yy = bkgd_pdf1(xx) #!
        print('# norm of bkgd pdf:', integrate.simps(yy, xx)) 
        exit()
    def bkgd_pdf1a(cos_zenith): #!
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec1, dec)/17032.062728182547/2./pi # for IC59
        #return use.f2a(bkgd_pdf_dec1, dec)/19492.124975830415/2./pi # For IC86_III
    
    i = 2; #!
    tmpDecs2 = loadtxt(filenms[i])[:,4]/d2r #!
    def bkgd_pdf_dec2(dec): #!
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-Dec_band; decUL = dec+Dec_band; 
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        print( 1/sqrt( len(where( (tmpDecs2>decLL)*(tmpDecs2<decUL) )[0]) ) )
        return len(where( (tmpDecs2>decLL)*(tmpDecs2<decUL) )[0])/Omega #!
    for i1 in range(0): # get the norm
        def bkgd_pdf2(cos_zenith): #!
            dec = arcsin( -cos_zenith )
            return use.f2a(bkgd_pdf_dec2, dec)  #!
        xx = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000) 
        yy = bkgd_pdf2(xx) #!
        print('# norm of bkgd pdf:', integrate.simps(yy, xx)) 
        exit()
    def bkgd_pdf2a(cos_zenith): #!
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec2, dec)/14824.35982956592/2./pi # For IC79
        #return use.f2a(bkgd_pdf_dec2, dec)/20210.568734579258/2./pi # For IC86_IV
    
    i = 3; #!
    tmpDecs3 = loadtxt(filenms[i])[:,4]/d2r #!
    def bkgd_pdf_dec3(dec): #!
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-Dec_band; decUL = dec+Dec_band; 
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        print( 1/sqrt( len(where( (tmpDecs3>decLL)*(tmpDecs3<decUL) )[0]) ) )
        return len(where( (tmpDecs3>decLL)*(tmpDecs3<decUL) )[0])/Omega #!
    for i1 in range(0): # get the norm
        def bkgd_pdf3(cos_zenith): #!
            dec = arcsin( -cos_zenith )
            return use.f2a(bkgd_pdf_dec3, dec)  #!
        xx = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000) 
        yy = bkgd_pdf3(xx) #!
        print('# norm of bkgd pdf:', integrate.simps(yy, xx)) 
        exit()
    def bkgd_pdf3a(cos_zenith): #!
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec3, dec)/21636.192271863227/2./pi # for IC86_I
        #return use.f2a(bkgd_pdf_dec3, dec)/20569.18429116335/2./pi # for IC86_V
    
    i = 4; #!
    tmpDecs4 = loadtxt(filenms[i])[:,4]/d2r #!
    def bkgd_pdf_dec4(dec): #!
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-Dec_band; decUL = dec+Dec_band; 
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        print( 1/sqrt( len(where( (tmpDecs4>decLL)*(tmpDecs4<decUL) )[0]) ) )
        return len(where( (tmpDecs4>decLL)*(tmpDecs4<decUL) )[0])/Omega #!
    for i1 in range(0): # get the norm
        def bkgd_pdf4(cos_zenith): #!
            dec = arcsin( -cos_zenith )
            return use.f2a(bkgd_pdf_dec4, dec)  #!
        xx = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000) 
        yy = bkgd_pdf4(xx) #!
        print('# norm of bkgd pdf:', integrate.simps(yy, xx)) 
        exit()
    def bkgd_pdf4a(cos_zenith): #!
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec4, dec)/121079.155595356/2./pi # IC86_II2VII
        #return use.f2a(bkgd_pdf_dec4, dec)/19670.4445981798/2./pi # for IC86_VI
    
    for i in range(0):
        i = 5; #!
        tmpDecs5 = loadtxt(filenms[i])[:,4]/d2r #!
        def bkgd_pdf_dec5(dec): #!
            if dec > 87./d2r or dec < -87./d2r:
                return 0
            decLL = dec-Dec_band; decUL = dec+Dec_band; 
            Omega = 2.*pi*( sin(decUL) - sin(decLL) )
            return len(where( (tmpDecs5>decLL)*(tmpDecs5<decUL) )[0])/Omega #!
        for i1 in range(0): # get the norm
            def bkgd_pdf5(cos_zenith): #!
                dec = arcsin( -cos_zenith )
                return use.f2a(bkgd_pdf_dec5, dec)  #!
            xx = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000) 
            yy = bkgd_pdf5(xx) #!
            print('# norm of bkgd pdf:', integrate.simps(yy, xx)) 
        def bkgd_pdf5a(cos_zenith): #!
            dec = arcsin( -cos_zenith )
            return use.f2a(bkgd_pdf_dec5, dec)/23183.583869891932/2./pi #!
    
    bkgd_pdfs = [] + [bkgd_pdf0a] + [bkgd_pdf1a] + [bkgd_pdf2a] + [bkgd_pdf3a] + [bkgd_pdf4a] #+ [bkgd_pdf5a]
    # Case i=1 was checked w/ an earlier data release but same peroid, consistent.

for i in range(0): # plot in cosz
    #
    'Plot to check bkgd pdfs'
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('linear')
    
    tmp8 = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 100+1)
    #ax.plot(tmp8, bkgd_pdf2a(tmp8)*2*pi,'-',label=r'2',lw=1.5,ms=2) #!
    #ax.plot(tmp8, bkgd_pdf3a(tmp8)*2*pi,'-',label=r'3',lw=1.5,ms=2) #!
    #ax.plot(tmp8, bkgd_pdf4a(tmp8)*2*pi,'-',label=r'4',lw=1.5,ms=2) #!
    
    i = 0
    ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2)
    #savetxt('data_output_new_data/bkgdpdf_cosz_IC40_101.txt', array([tmp8, bkgd_pdfs[i](tmp8)]).T )
    tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC40_101.txt').T
    ax.plot(tmp8[0], tmp8[1]*2*pi,'m--',label=r'',lw=1.5,ms=2)
    i = 1
    #ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2)
    #savetxt('data_output_new_data/bkgdpdf_cosz_IC59_101.txt', array([tmp8, bkgd_pdfs[i](tmp8)]).T )
    tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC59_101.txt').T
    ax.plot(tmp8[0], tmp8[1]*2*pi,'g-',label=r'',lw=1.5,ms=2)
    i = 2
    #ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2)
    #savetxt('data_output_new_data/bkgdpdf_cosz_IC79_101.txt', array([tmp8, bkgd_pdfs[i](tmp8)]).T )
    tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC79_101.txt').T
    ax.plot(tmp8[0], tmp8[1]*2*pi,'b-',label=r'',lw=1.5,ms=2)
    i = 3
    #ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2)
    #savetxt('data_output_new_data/bkgdpdf_cosz_IC86a_101.txt', array([tmp8, bkgd_pdfs[i](tmp8)]).T )
    tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC86a_101.txt').T
    ax.plot(tmp8[0], tmp8[1]*2*pi,'r-',label=r'',lw=1.5,ms=2)
    i = 4
    #ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2)
    #savetxt('data_output_new_data/bkgdpdf_cosz_IC86b_101.txt', array([tmp8, bkgd_pdfs[i](tmp8)]).T )
    tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC86b_101.txt').T
    ax.plot(tmp8[0], tmp8[1]*2*pi,'k-',label=r'',lw=1.5,ms=2)

    ax.text(-0.14, 0.183, r'IC86-II to IC86-VII', color='k', size=18, rotation=0)
    ax.text(0.153, 0.483, r'IC86-I', color='r', size=18, rotation=0)
    ax.text(0.12, 0.79, r'IC79', color='b', size=18, rotation=0)
    ax.text(0.4, 0.735, r'IC59', color='g', size=18, rotation=0)
    ax.text(0.7, 0.64, r'IC40', color='m', size=18, rotation=0)

    
    ax.set_xlim(-1,1); ax.set_ylim(0,1.05)
    # ax.set_xlim(-90,90); ax.set_ylim(0,1.1)
    # ax.set_xlabel(r"Dec",fontsize=20, labelpad=None) 
    ax.set_xlabel(r"$\cos$(zenith angle) or -$\sin$(Dec)",fontsize=20, labelpad=None) 
    ax.set_ylabel(r"Background PDF",fontsize=20)
    #ax.legend(loc='best',prop={'size':14}) 
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) 
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    ax.yaxis.get_ticklocs(minor=True)
    ax.minorticks_on()
    #plt.grid()
    plt.show()
    exit()
for i in range(0): # plot in Dec
    #
    'Plot to check bkgd pdfs'
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('linear')
    
    tmp8 = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000)
    #ax.plot(tmp8, bkgd_pdf2a(tmp8)*2*pi,'-',label=r'2',lw=1.5,ms=2) #!
    #ax.plot(tmp8, bkgd_pdf3a(tmp8)*2*pi,'-',label=r'3',lw=1.5,ms=2) #!
    #ax.plot(tmp8, bkgd_pdf4a(tmp8)*2*pi,'-',label=r'4',lw=1.5,ms=2) #!
    
    for i in range(len(filenms)):
        # ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2)  # bkgdpdf v.s. cos zenith
        ax.plot( arccos(tmp8)*d2r-90., bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2) #! # bkgdpdf v.s. 
    
    #ax.set_xlim(-1,1); 
    ax.set_xlim(-90,90); ax.set_ylim(0,1.1)
    ax.set_xlabel(r"Dec",fontsize=20, labelpad=None) 
    #ax.set_xlabel(r"$\cos$(zenith)",fontsize=20, labelpad=None) 
    ax.set_ylabel(r"Probability density [ ]",fontsize=20)
    ax.legend(loc='best',prop={'size':14}) 
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) 
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    plt.grid()
    plt.show()
    exit()


'############# Background spatial and energy PDFs ##############'
## First read all the files
## Then choose a Dec
## Then do the energy sliding winow in log
## Might merge with the code above.

#filenms = array(['data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC40_exp.csv'])  ###!!! # cdx
#filenms = array(['data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC59_exp.csv']) # cdx
#filenms = array(['data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC79_exp.csv']) # cdx
#filenms = array(['data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC86_I_exp.csv']) # cdx
filenms = array(['data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC86_II2VII_exp_BZ.csv']) # cdx

' Bkgd spatial pdf '  # using sliding window in cosz
i = 0; #!
tmp_Decs = loadtxt(filenms[i])[:,4]/d2r #!
tmp_cosz = -sin(tmp_Decs)

def bkgd_pdf_spatial0(cosz): #
    #
    #if dec > 87./d2r or dec < -87./d2r:
    #    return 0
    #decLL = dec-Dec_band; decUL = dec+Dec_band; 
    dcosz = 0.1/2. \
            #
            # consistent with the largest zenith band of the previous choice Dec_band=3/d2r bcuz cos(90/d2r-3/d2r)-cos(90/d2r+3/d2r)=0.1047;
    if cosz-dcosz < -1.:
        #
        idx = where( (tmp_cosz >= -1.)*(tmp_cosz <= cosz+dcosz) ) 
        Omega = 2.*pi*( cosz+dcosz+1 ) #e.g., -0.97+0.05=-0.92, %+1=0.08
    elif cosz+dcosz > 1.:
        #
        idx = where( (tmp_cosz >= cosz-dcosz)*(tmp_cosz <= 1.) ) 
        Omega = 2.*pi*( 1-(cosz-dcosz) ) #e.g., 0.97-0.05=0.92, 1-%=0.08
    else:
        #
        idx = where( (tmp_cosz >= cosz-dcosz)*(tmp_cosz <= cosz+dcosz) ) 
        Omega = 2.*pi*dcosz*2
    Nums = len( idx[0] )
    return Nums/Omega
for i1 in range(1): # get the norm
    #
    def bkgd_pdf_spatial0_array(cosz): #!
        return use.f2a(bkgd_pdf_spatial0, cosz)  #!
    #xx = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 1000) 
    xx = linspace(-1, 1, 1000) 
    yy = bkgd_pdf_spatial0_array(xx) #!
    norm = integrate.simps(yy, xx)
    #print('# norm of bkgd pdf:', norm) 
    #exit()
# norm = 121181.9732681692 # for IC86b
def bkgd_pdf_spatial(cosz): #!
    return use.f2a(bkgd_pdf_spatial0, cosz)/norm/2./pi 

for i in range(0): # plot bkgd spt pdf
    #
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('linear')
    
    tmp = loadtxt('data_output_new_data/bkgdpdf_cosz_IC86b_101.txt').T # To compare with the previous results using sliding window in angle
    ax.plot(tmp[0], tmp[1]*2*pi,'b-',label=r'',lw=1.5,ms=2) 

    xx = linspace(-1, 1, 100) 
    yy = bkgd_pdf_spatial(xx) #!
    ax.plot(xx, yy*2*pi,'r-',label=r'',lw=1.5,ms=2) 
    
    ax.set_xlim(-1,1)
    #use.autoscale_y(ax)
    #ax.set_ylim(0.2, 0.7)
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=22)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=22)
    plt.grid()#ls='-', lw=0.5)
    plt.show()
    
    exit()


' Bkgd E pdf '
'for a different dataset, the only thing to change is filenms'
i = 0; 
tmp_Decs = loadtxt(filenms[i])[:,4]/d2r; tmp_cosz = -sin(tmp_Decs)
tmp_lgEpr = loadtxt(filenms[i])[:,1]
def bkgd_pdf_E(cosz, lgEpr):
    global tmp_cosz, tmp_lgEpr

    'Get the events in the nearby Dec range'
    if cosz-0.05 < -1.:
        idx = where( (tmp_cosz >= -1.)*(tmp_cosz <= -1.+0.05*2) ) 
    elif cosz+0.05 > 1.:
        idx = where( (tmp_cosz >= 1.-0.05*2)*(tmp_cosz <= 1.) ) 
    else:
        idx = where( (tmp_cosz >= cosz-0.05)*(tmp_cosz <= cosz+0.05) )
    tmp1_cosz = tmp_cosz[idx]; tmp1_lgEpr = tmp_lgEpr[idx] # These two arrays will be used for the following analysis in this func

    lgEmin = tmp1_lgEpr.min(); lgEmax = tmp1_lgEpr.max()
    #print( '10**lgEmin, 10**lgEmax', 10**lgEmin, 10**lgEmax )
    
    'Get the tot num of events in the nearby energy range'
    'Sliding the energy window'
    def bkgd_pdf_E_cosz(lgEpr):
        Num = len(where( (tmp1_lgEpr > lgEpr-0.2)*(tmp1_lgEpr < lgEpr+0.2) )[0]) #!
        return Num
    
    def bkgd_pdf_E_array(lgEpr): #!
        return use.f2a(bkgd_pdf_E_cosz, lgEpr)  #!
    
    xx = linspace( lgEmin, lgEmax, 1000 )
    yy = bkgd_pdf_E_array(xx) #!
    norm = integrate.simps(yy, xx)
    
    return use.f2a(bkgd_pdf_E_cosz, lgEpr)/norm

'############ !Background spatial and energy PDFs ! #############'


for i2 in range(1): # Calc bkgd E pdf for each event
    # To calc for another dataset, just chagne "filenms" above, mark by '##!!'
    #tmp1 = loadtxt('data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/upgoing_events.txt') # for rdpc Nicolas ppr
    tmp1 = loadtxt(filenms[0])
    for i in tqdm.tqdm( range(tmp1.size) ):
        cosz_ = -sin(tmp1[i,4]/d2r)
        lgEpr_ = array([ tmp1[i,1] ])
        print(i,' ', tmp1[i,4],'  ', lgEpr_[0],' ', bkgd_pdf_E( cosz_, lgEpr_ )[0] )

for i2 in range(0): # Calc bkgd E pdf for each SN
    # To calc for another dataset, just chagne "filenms" above, mark by '##!!'
    #tmp1 = loadtxt('../20210323_cjSN/20210300_cjSN/data_input/SNe_Ibc_29.txt')
    tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/10_yr_analysis/SNe_data_IC/SNe_Dec_IC86b.txt') ##!!
    for i in range( len(tmp1) ):
        cosz_ = -sin(tmp1[i,3])    ##################!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        Epr_ = use.ebs(1e2, 1e9, 7*10)
        lgEpr_ = log10( Epr_ )
        #lgEpr_ = array([ tmp1[i,1] ])
        print( '# SN num = ', i, ' Dec = ', tmp1[i,3]*d2r )  ###############!!!!!!!!!!!!!!!!!!!!!
        print( bkgd_pdf_E( cosz_, lgEpr_ ) )

# Calc the 2D (cosz, E) bkgd pdf distribution
coszs = linspace(-1, 1, 200+1)
lgEprs  = log10( use.ebs(1e1, 1e8, 7*30) )
bkgd_pdf_2D = zeros(( len(coszs), len(lgEprs) ))

bkgd_pdfs_spt = bkgd_pdf_spatial( coszs )
for i in range(len(coszs)):
    tmp2 = bkgd_pdf_E( coszs[i], lgEprs )
    print(i)
    print( integrate.simps(tmp2, lgEprs) ) # check if normalized
    #print(tmp2)
    #exit()
    bkgd_pdf_2D[i] = tmp2 * bkgd_pdfs_spt[i]

savetxt('ttt_bkgd_pdf_2D_86b.txt', bkgd_pdf_2D) ###!!!


# not very important
for i in range(0): # plot sth
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('log'); ax.set_yscale('log')
    
    ax.plot(10**xx, yy,'ro-',label=r'',lw=1.5,ms=1) 
    #tmp = loadtxt('data_input/1706.02175_fig2_left_Bpdf.dat').T
    #ax.plot(tmp[0], tmp[1], 'b--',label=r'',lw=1.5,ms=2) 
    
    #ax.set_xlabel(r"$E$  [ GeV ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    #ax.set_ylabel(r"$E^2dN/dE$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
    ax.set_xlim()
    #use.autoscale_y(ax)
    ax.set_ylim()
    #ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=22)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=22)
    for i in range(1): 
        # fix the issue of ticks missing when axis range > 10 decades
        import matplotlib.ticker 
        #Basically know how it works, not totally
        #Used locmaj_x, _y different because problem happens when using same
        locmaj_x = matplotlib.ticker.LogLocator(base=10.0, subs=(1.0, ), numticks=100)
        locmin_x = matplotlib.ticker.LogLocator(base=10.0, subs=arange(2, 10) * .1,
                numticks=100)
        ax.xaxis.set_major_locator(locmaj_x)
        ax.xaxis.set_minor_locator(locmin_x)
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    
        locmaj_y = matplotlib.ticker.LogLocator(base=10.0, subs=(1.0, ), numticks=100)
        locmin_y = matplotlib.ticker.LogLocator(base=10.0, subs=arange(2, 10) * .1,
                numticks=100)
        ax.yaxis.set_major_locator(locmaj_y)
        ax.yaxis.set_minor_locator(locmin_y)
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    plt.grid()#ls='-', lw=0.5)
    plt.show()
for i in range(0): # rpdc the two figs of Nicolas ppr
    #
    #filenms = array(['data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/all_events.txt'])  #!
    filenms = array(['./data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC86_I_exp.csv']) # cdx

    i = 0; 
    tmp_Decs3 = loadtxt(filenms[i])[:,4]/d2r 
    tmp_lgEpr = 10**loadtxt(filenms[i])[:,1]
    
    tmp_cosz = -sin(tmp_Decs3)
    #idx = where( (tmp_cosz>-0.1)*(tmp_cosz<0.0) )  #!
    idx = where( (tmp_cosz>-0.174)*(tmp_cosz<0.174) )  
    #idx = where( (tmp_cosz>=-1.)*(tmp_cosz<-0.9) ) 
    print( len(idx[0]) )
    tmp_cosz = tmp_cosz[idx]
    tmp_lgEpr = tmp_lgEpr[idx]
    
    print( tmp_lgEpr.min(), tmp_lgEpr.max() ) # 61.66, 14791.
    binss = use.ebs( tmp_lgEpr.min(), tmp_lgEpr.max(), 30 )
    Nums = histogram( tmp_lgEpr, binss)[0]
    bin_Cs = (binss[:-1] + binss[1:])/2.
    bin_err = ( binss[1]-binss[0] )/2.
    norm = integrate.simps( Nums, log10(bin_Cs) )
    Nums_err = sqrt(Nums)/norm
    Nums =  Nums/norm
    #print( norm )
    #exit()
    
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('log'); ax.set_yscale('log')
    tmp = loadtxt('data_input/1706.02175_fig2_right_Bpdf.dat').T #!
    ax.plot(tmp[0], tmp[1],'r--',label=r'',lw=1.5,ms=2) 
    #tmp = loadtxt('data_input/1706.02175_fig2_left_Bpdf.dat').T
    #ax.plot(tmp[0], tmp[1],'r--',label=r'',lw=1.5,ms=2) 
    
    ax.plot(bin_Cs, Nums,'b-',label=r'',lw=1.5,ms=2) 
    plt.errorbar(bin_Cs, Nums, xerr=bin_err, yerr=Nums_err, fmt ='bo', capsize=2,ms=4, label=r'')
    savetxt( 'tmp.txt', array([ bin_Cs, Nums ]).T )
    
    #ax.set_xlabel(r"$E$  [ GeV ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    #ax.set_ylabel(r"$E^2dN/dE$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
    ax.set_xlim(20,2e5)
    use.autoscale_y(ax)
    ax.set_ylim()
    #ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=22)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=22)
    plt.grid()#ls='-', lw=0.5)
    plt.show()
    #plt.savefig('',,bbox_inches='tight', pad_inches=0.1)



# bkup

# Xcheck bkgd pdf between sliding window and binning; Consistent
for ii1 in range(0):
    #
    filenms = array([ 
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC40_exp.csv', # cdx
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC59_exp.csv', # cdx
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC79_exp.csv', # cdx
        #'./data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC79-2010-events.txt',
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC86_I_exp.csv', # cdx
        #'./data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC86-2011-events.txt',
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/IC86_II2VII_exp_BZ.csv', # cdx
        ]) #!
    
    i = 2; #!
    num_bins = 100 #!
    
    cosz_nu = cos( loadtxt(filenms[i])[:,-1]/d2r )
    Ntot = len(cosz_nu)
    norm = Ntot * 2./num_bins
    cosz_b = linspace(-1., 1., num_bins+1)
    cosz_c = cosz_b[1:]/2. + cosz_b[:-1]/2.
    Nums = histogram( cosz_nu, cosz_b)[0]/norm
    
    
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('linear')
    
    ax.plot(cosz_c, Nums,'ro-',label=r'',lw=1.5,ms=2) 
    if i == 0:
        tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC40_101.txt').T
    elif i == 1:
        tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC59_101.txt').T
    elif i == 2:
        tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC79_101.txt').T
    elif i == 3:
        tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC86a_101.txt').T
    elif i == 4:
        tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC86b_101.txt').T
    ax.plot(tmp8[0], tmp8[1]*2*pi,'m-',label=r'',lw=1.5,ms=2)
    
    #ax.set_xlabel(r"$E$  [ GeV ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    #ax.set_ylabel(r"$E^2dN/dE$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
    ax.set_xlim()
    use.autoscale_y(ax)
    ax.set_ylim()
    ax.set_xlim(-1,1); ax.set_ylim(0,1.05)
    ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=22)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=22)
    plt.grid()#ls='-', lw=0.5)
    plt.show()
