#!/usr/bin/python
import tqdm

'''
# Initally copied from likelihood_v3.py and modified the single source analysis part to accelerate.
# In this version I am going to revise the single src analysis code to make it faster, in order to run >1e6 simulations.
# In the modified version, S/B pdf are only calc'd once when maximizing the TS.  Only the single src analysis calc was changed.
'''

'#####################  ######################'
'#################### !! #####################'

from numpy import *
d2r = 180./pi

'################################### Input ####################################'
gamma = -2.00; 
#gamma = -2.53; 
#gamma = -3.00; 

IF_BKGD_PDF = True
IF_stacking_anlys_calc_PDFs = True
#IF_BKGD_PDF = False
#IF_stacking_anlys_calc_PDFs = False

#IF_equal_weighting = True
IF_equal_weighting = False

' Need to compare the TS with the plot, cuz sometimes it cannot find the maximum. If not, change the value in line ~669, under function max_TS_tot_().'
'################################## !Input! ###################################'
#IF_single_src_anlys = True
IF_single_src_anlys = False

IF_stacking_anlys_calc_results = True  
#IF_stacking_anlys_calc_results = False

print('# gamma = ', gamma, '. Do not forget here!!!!!!') 


################################## Sources ####################################
from source import *
#N_src_south = len(where(Decs_src <0)[0])
#N_src_north = len(where(Decs_src >0)[0])
################################# !Sources! ###################################


################################## Neutrinos ##################################
from neutrinos_data import *
################################# !Neutrinos! #################################


################################### uptime ####################################
uptime_flms = array([
    './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC40_exp.csv',\
    './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC59_exp.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC79_exp.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_I_exp.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_II2VII_exp_BZ.csv',
    ]) 

uptimes = zeros( len(uptime_flms) );
for i in range(len(uptime_flms)):
    tmp = loadtxt(uptime_flms[i])
    uptimes[i] = sum(tmp[:,1]-tmp[:,0]) / 365.25
################################## !uptime! ###################################


# re-import the packages cuz importing the files above disturbed some of them.
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
from scipy.optimize import minimize
from scipy.stats import norm
import os,datetime
import use
set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=6, floatmode='maxprec')


############################## EA and f_k  ####################################
EAfilenms = array([ 
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC40_effectiveArea.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC59_effectiveArea.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC79_effectiveArea.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_I_effectiveArea.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_II_effectiveArea.csv',
    ])


# To get the w_acc(coszenith)
EAs = loadtxt(EAfilenms[0]) \
        # 40 Es, 50 angles equally binned in cosz or sinDec
        # Ec,min = 10**2.1 = 125.9 GeV, file.
Es = 10**( unique(EAs[:,0] )/2.+unique( EAs[:,1])/2. ) 
coszeniths = ( cos(90./d2r + unique(EAs[:,2])/d2r) + cos(90./d2r + unique(EAs[:,3])/d2r) )/2. 

W_accs = []
for i in range(1):
    i = 0; 
    EAs = loadtxt(EAfilenms[i]) # 40 Es, 50 angles
    Aeff = EAs[:,4]; Aeff = Aeff.reshape( len(coszeniths),-1 ) 
    W_acc_dat0 = integrate.simps( Es.reshape(1,-1)**(gamma+1.)*Aeff, log(Es), axis=1 ) #checked 
    W_acc0 = intp.interp1d( coszeniths, W_acc_dat0, kind='linear', bounds_error=False, fill_value='extrapolate') 
    
    
    i = 1; 
    EAs = loadtxt(EAfilenms[i]) # 40 Es, 50 angles
    Aeff = EAs[:,4]; Aeff = Aeff.reshape( len(coszeniths),-1 ) 
    W_acc_dat1 = integrate.simps( Es.reshape(1,-1)**(gamma+1.)*Aeff, log(Es), axis=1 ) #checked 
    W_acc1 = intp.interp1d( coszeniths, W_acc_dat1, kind='linear', bounds_error=False, fill_value='extrapolate') 
    
    
    i = 2; 
    EAs = loadtxt(EAfilenms[i]) # 40 Es, 50 angles
    Aeff = EAs[:,4]; Aeff = Aeff.reshape( len(coszeniths),-1 ) 
    W_acc_dat2 = integrate.simps( Es.reshape(1,-1)**(gamma+1.)*Aeff, log(Es), axis=1 ) #checked 
    W_acc2 = intp.interp1d( coszeniths, W_acc_dat2, kind='linear', bounds_error=False, fill_value='extrapolate') 
    
    
    i = 3; 
    EAs = loadtxt(EAfilenms[i]) # 40 Es, 50 angles
    Aeff = EAs[:,4]; Aeff = Aeff.reshape( len(coszeniths),-1 ) 
    W_acc_dat3 = integrate.simps( Es.reshape(1,-1)**(gamma+1.)*Aeff, log(Es), axis=1 ) #checked 
    W_acc3 = intp.interp1d( coszeniths, W_acc_dat3, kind='linear', bounds_error=False, fill_value='extrapolate') 
    
    
    i = 4; 
    EAs = loadtxt(EAfilenms[i]) # 40 Es, 50 angles
    Aeff = EAs[:,4]; Aeff = Aeff.reshape( len(coszeniths),-1 ) 
    W_acc_dat4 = integrate.simps( Es.reshape(1,-1)**(gamma+1.)*Aeff, log(Es), axis=1 ) #checked 
    W_acc4 = intp.interp1d( coszeniths, W_acc_dat4, kind='linear', bounds_error=False, fill_value='extrapolate') 

W_accs += [W_acc0, W_acc1, W_acc2, W_acc3, W_acc4]


for i in range(0):  # plot W_acc_dat0 and compare with old data
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('linear')

    plt.plot( -coszeniths, W_acc_dat4, 'ro--', label=r'2, '+str(gamma), lw=1.5, ms=2 )

    #EAs = loadtxt('./data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC79-2010-TabulatedAeff.txt')
    EAs = loadtxt('./data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC86-2012-TabulatedAeff.txt')
    Es = sqrt( unique(EAs[:,0] )*unique( EAs[:,1]) ) 
    coszeniths0 = ( unique(EAs[:,2])+unique(EAs[:,3]) )/2. # checked 
    Aeff = EAs[:,4]*1e4
    Aeff = Aeff.reshape(-1,200) # Each row has same energy, checked
    W_acc_dat0 = integrate.simps( Es.reshape(-1,1)**(gamma+1.)*Aeff, log(Es), axis=0 ) #checked # gamma+1 cuz int in log 
    plt.plot( -coszeniths0, W_acc_dat0, 'bo-', label=r'2, '+str(gamma), lw=1.5, ms=2 )



    ax.set_xlabel(r"sin Dec",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    ax.set_ylabel(r"W_acc",fontsize=20)
    ax.set_xlim(-1,1)
    #use.autoscale_y(ax)
    ax.set_ylim()
    ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    plt.grid()#ls='-', lw=0.5)
    plt.show()
    exit()
for i in range(0):  # plot W_accs
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('log')

    coszenithsA = linspace(-1,1,1000)
    plt.plot( -coszenithsA, W_accs[0](coszenithsA), label=r'0, '+str(gamma) )
    plt.plot( -coszenithsA, W_accs[1](coszenithsA), label=r'1, '+str(gamma) )
    plt.plot( -coszenithsA, W_accs[2](coszenithsA), label=r'2, '+str(gamma) )
    plt.plot( -coszenithsA, W_accs[3](coszenithsA), label=r'3, '+str(gamma) )
    plt.plot( -coszenithsA, W_accs[4](coszenithsA), label=r'4, '+str(gamma) )

    plt.plot( [sin(-5./d2r)]*2, [0,1], 'k--', label=r'Dec = $-5^\circ$' )

    ax.set_xlabel(r"sin Dec",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    ax.set_ylabel(r"W_acc",fontsize=20)
    ax.set_xlim()
    #use.autoscale_y(ax)
    ax.set_ylim(1e-4,1)
    ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    plt.grid()#ls='-', lw=0.5)
    plt.show()
    exit()

# W_accs_src for each sample
tmp0 = W_accs[0]( -sin(Decs_src) ) * uptimes[0] 
tmp1 = W_accs[1]( -sin(Decs_src) ) * uptimes[1]
tmp2 = W_accs[2]( -sin(Decs_src) ) * uptimes[2]
tmp3 = W_accs[3]( -sin(Decs_src) ) * uptimes[3]
tmp4 = W_accs[4]( -sin(Decs_src) ) * uptimes[4]
W_accs_src = array( [tmp0, tmp1, tmp2, tmp3, tmp4] )
del( tmp0, tmp1, tmp2, tmp3, tmp4 )

############################# !EA and f_k ! ###################################


############################### Background PDF ################################
# '''
'This block continues prev block.  So can put in the same file.'
'from background_pdf.py, using sliding window'
'Later make below to a cycle'

filenms = array([  # Donot use the neutrinos_data.py do calc the bkgd pdf, cuz the analysis region may be smaller than <87deg.
    './data_input/IceCube_data_released/icecube_10year_ps/events/IC40_exp.csv',\
    './data_input/IceCube_data_released/icecube_10year_ps/events/IC59_exp.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/events/IC79_exp.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/events/IC86_I_exp.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/events/IC86_II2VII_exp_BZ.csv',]) 

Nks_tot = array( zeros(len(filenms)), dtype=int ) # Used to renormalize the bkgdpdf
for j2 in range( len(filenms) ):
    Nus = loadtxt( filenms[j2] )
    idx = where( (Nus[:,4]>-87.)*(Nus[:,4]<87.) )[0]
    Nks_tot[j2] = len( idx )

bkgd_pdfs = []
if IF_BKGD_PDF:
    i9 = 0;
    num_events0 = Nks_tot[i9]
    tmpDecs0 = loadtxt(filenms[i9])[:,4]/d2r 
    def bkgd_pdf_dec0(dec): 
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-3./d2r; decUL = dec+3./d2r; 
        #print( 'dec, decLL, decUL', dec*d2r, decLL*d2r, decUL*d2r)
        #exit()
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        return len(where( (tmpDecs0>decLL)*(tmpDecs0<decUL) )[0])/Omega 
    def bkgd_pdf0a(cos_zenith): 
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec0, dec)/num_events0
    
    i9 = 1; 
    num_events1 = Nks_tot[i9]
    tmpDecs1 = loadtxt(filenms[i9])[:,4]/d2r 
    def bkgd_pdf_dec1(dec): 
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-3./d2r; decUL = dec+3./d2r; 
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        return len(where( (tmpDecs1>decLL)*(tmpDecs1<decUL) )[0])/Omega 
    def bkgd_pdf1a(cos_zenith): 
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec1, dec)/num_events1
    
    i9 = 2; 
    num_events2 = Nks_tot[i9]
    tmpDecs2 = loadtxt(filenms[i9])[:,4]/d2r 
    def bkgd_pdf_dec2(dec): 
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-3./d2r; decUL = dec+3./d2r; 
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        return len(where( (tmpDecs2>decLL)*(tmpDecs2<decUL) )[0])/Omega 
    def bkgd_pdf2a(cos_zenith): 
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec2, dec)/num_events2
    
    i9 = 3; 
    num_events3 = Nks_tot[i9]
    tmpDecs3 = loadtxt(filenms[i9])[:,4]/d2r 
    def bkgd_pdf_dec3(dec): 
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-3./d2r; decUL = dec+3./d2r; 
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        return len(where( (tmpDecs3>decLL)*(tmpDecs3<decUL) )[0])/Omega 
    def bkgd_pdf3a(cos_zenith): 
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec3, dec)/num_events3 #21636.192271863227/2./pi 
    
    i9 = 4; 
    num_events4 = Nks_tot[i9]
    tmpDecs4 = loadtxt(filenms[i9])[:,4]/d2r 
    def bkgd_pdf_dec4(dec): 
        if dec > 87./d2r or dec < -87./d2r:
            return 0
        decLL = dec-3./d2r; decUL = dec+3./d2r; 
        Omega = 2.*pi*( sin(decUL) - sin(decLL) )
        return len(where( (tmpDecs4>decLL)*(tmpDecs4<decUL) )[0])/Omega 
    def bkgd_pdf4a(cos_zenith): 
        dec = arcsin( -cos_zenith )
        return use.f2a(bkgd_pdf_dec4, dec)/num_events4
    
    
    bkgd_pdfs = [] + [bkgd_pdf0a] + [bkgd_pdf1a] + [bkgd_pdf2a] + [bkgd_pdf3a] + [bkgd_pdf4a] 
    # Case i=1 was checked w/ an earlier data release but same peroid, consistent.
    
    # This part should not be used.
    ## Below changes the bkgd pdf by only a few in 1e4, and changes the ns_95% by a few %, which is negligible.  I geuss sqrt(a few in 1e4) -> a few %
    #xxx = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000)
    #yyy0 = bkgd_pdf0a(xxx)
    #bkgd_pdf0b = intp.interp1d( xxx, yyy0, kind='linear', bounds_error=True, fill_value=0)
    #yyy1 = bkgd_pdf1a(xxx)
    #bkgd_pdf1b = intp.interp1d( xxx, yyy1, kind='linear', bounds_error=True, fill_value=0)
    #yyy2 = bkgd_pdf2a(xxx)
    #bkgd_pdf2b = intp.interp1d( xxx, yyy2, kind='linear', bounds_error=True, fill_value=0)
    #yyy3 = bkgd_pdf3a(xxx)
    #bkgd_pdf3b = intp.interp1d( xxx, yyy3, kind='linear', bounds_error=True, fill_value=0)
    #yyy4 = bkgd_pdf4a(xxx)
    ##print('2*pi*integrate.trapz( yyy4, xxx )-1', 2*pi*integrate.trapz( yyy4, xxx )-1 )
    #bkgd_pdf4b = intp.interp1d( xxx, yyy4, kind='linear', bounds_error=True, fill_value=0)
    #bkgd_pdfs = [] + [bkgd_pdf0b] + [bkgd_pdf1b] + [bkgd_pdf2b] + [bkgd_pdf3b] + [bkgd_pdf4b]  
    
    for i in range(0):
        'Plot to check bkgd pdfs'
        fig = plt.figure(figsize=(6, 6), facecolor='w')
        ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
        ax.set_xscale('linear'); ax.set_yscale('linear')
        
        tmp8 = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000)
        #ax.plot(tmp8, bkgd_pdf2a(tmp8)*2*pi,'-',label=r'2',lw=1.5,ms=2) 
        #ax.plot(tmp8, bkgd_pdf3a(tmp8)*2*pi,'-',label=r'3',lw=1.5,ms=2) 
        #ax.plot(tmp8, bkgd_pdf4a(tmp8)*2*pi,'-',label=r'4',lw=1.5,ms=2) 
        
        for i in range(len(filenms)):
            #ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2) 
            ax.plot(arccos(tmp8)*d2r-90, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2) 
        
        #ax.set_xlim(-1,1); ax.set_ylim(0,1)
        #ax.set_xlabel(r"$\cos$(zenith)",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
        ax.set_xlabel(r"Dec [ Degrees ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
        ax.set_ylabel(r"Probability density [ ]",fontsize=20)
        ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
        ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
        ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
        ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
        plt.grid()#ls='-', lw=0.5)
        plt.show()
        exit()
# '''
 

############################## !Background PDF! ###############################

'########################## Single source analysis #############################'

ROI = 20./d2r 
print( '# ROI =', ROI*d2r )

def SnB_PDF(j):
    RA_src = RAs_src[j]; Dec_src = Decs_src[j]; 

    S_ji = [];  B_i = []; Nj = []
    for k in range( len(Nks) ):
        RAs_nu1D = RAs_nu[k, 0:Nks[k]]
        Decs_nu1D = Decs_nu[k, 0:Nks[k]]
        sgms_nu1D = sgms_nu[k, 0:Nks[k]]

        ang_dis = cos(RA_src-RAs_nu1D)*cos(Dec_src)*cos(Decs_nu1D) + sin(Dec_src)*sin(Decs_nu1D) 
        ang_dis[ where(ang_dis<-1.) ] = -1.
        ang_dis[ where(ang_dis> 1.) ] = 1. \
                # Very low chance to have nums like -1.0000000027831957 in arccos() probably due to truncation error, which gives "RuntimeWarning: invalid value encountered in arccos". Won't change the rlst cuz the nu is so far from the src.  # Adding this slows the code...
        ang_dis = arccos( ang_dis ) 

        #tmp_idx = where( ang_dis**2 < ROI**2. ) # circular ROI
        tmp_idx = where( abs( Dec_src-Decs_nu1D ) <= ROI ) # Dec band ROI

        RAs_nu1D1  = RAs_nu1D[tmp_idx]; 
        Decs_nu1D1 = Decs_nu1D[tmp_idx]; 
        sgms_nu1D1 = sgms_nu1D[tmp_idx];
        ang_dis1 = ang_dis[tmp_idx]

        Njk = len(RAs_nu1D1); Nj += [Njk]
        spatial_facs = 1./(2.*pi*sgms_nu1D1**2.)*exp( -(ang_dis1**2)/(2.*sgms_nu1D1**2.) )
        S_jik = spatial_facs
        S_ji = S_ji + [S_jik]

        B_ik = bkgd_pdfs[k]( -sin( Decs_nu1D1 ) )*Nks[k]/Njk # better pdf  
        print('!!!!!!!!!!!! Check the code here next time using, due to the Bpdf normalization issue found ~20250303.')
        B_i += [B_ik]
    return S_ji, B_i, Nj

def logL_j(j, n_s): 
    logL_j = 0;
    for k in range( len(Nks) ):

        L_jik = float( n_s*fks[k] )/float(Nj[k])*S_ji[k] +\
                ( 1. - float( n_s*fks[k] )/float(Nj[k]) )*B_i[k]
        if L_jik.min() < 0:
            'To avoid log(0.) which happens when n_s < 0. Wont affect the results at all if not do this cuz the n_s < 0 srcs are thrown away.'
            return 1e99, Nj[k]
        logL_jik = log(L_jik)

        logL_j = logL_j + logL_jik.sum()

    return logL_j, sum(array(Nj)) # maybe don't output Nk?

def TS_j(j, n_s):
    'Same as likelihood_reproduce_1810.02823.py'
    tmp3 = logL_j(j,n_s)[0]
    return 2.*( tmp3 - logL_j(j, 0.)[0] ) # code can be optimized here.

def max_TS_j1(j): # n_s can be any real number
    'Same as likelihood_reproduce_1810.02823.py'
    Nj = logL_j(j, 0.)[1]
    if Nj == 0:
        return -999, -999

    def TS_j1(n_s):
        return -TS_j(j, n_s)
    #bnds = ( (None, float(Nj)), ) # has to have ',' here smh... 
    #bnds = ( (0., float(Nj)), ) # has to have ',' here smh... 
    bnds = ( (-10., float(Nj)), ) 
        # has to have ',' here smh... # just pick a negative number as lower bound cuz if it's too small the L(n_s)/L(0) could overflow. The choice won't affect the results.
    res = minimize(TS_j1, (0.), method='SLSQP', bounds=bnds) 
    max_TS_j = -1*res.get('fun'); max_ns = res.get('x')[0];
    return array([ Nj, max_TS_j, max_ns ])

################### For catelog !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
if IF_single_src_anlys:
    rslt_single_src_analys = zeros( (N_src, 7) )
    for j1 in range(N_src):
        fks = W_accs_src[:,j1]/W_accs_src[:,j1].sum()  
        #print(fks)
        S_ji, B_i, Nj =  SnB_PDF(j1)
        tmp1 = max_TS_j1(j1)
        #print( j1, '  ', tmp1[0], '  ', tmp1[1], '  ', tmp1[2] )

        from scipy.stats import chi2
        dof=1.; p_loc   = chi2.sf(tmp1[1], dof)/2 # /2 bcuz degeneracy of a TS correspond to ns, one positive, the other negative.
        rslt_single_src_analys[j1] = array([ j1, tmp1[0], tmp1[1], tmp1[2], p_loc, RAs_src[j1]*d2r, Decs_src[j1]*d2r ])
        print( j1, '  ', tmp1[0], '  ', tmp1[1], '  ', tmp1[2], '  ', p_loc, '  ', RAs_src[j1]*d2r, '  ', Decs_src[j1]*d2r  )
        # index of src,  N of nus,        TS,         \hat{ns_}
    savetxt('ttt.txt', rslt_single_src_analys)
    
    for i in range(1): # process data and plot !!!!!!!!!!!!!!!!!!!!!!
        #rslt_f_nm = 'data_output_3yr_moslty/RQs3386_3yrNu_TS_dist_GM2.5.dat' 
        #rslt_f_nm = 'data_output/RQs3386_3yrNu_TS_dist_oldFks.dat' 
        #rslt_f_nm = 'data_output_test_code_v3/RQs3386_3yrNu_TS_dist_GM2.5_v2code.dat' 
        #rslt_f_nm = 'data_output_new_data/RQs3386_10yrNu_TS_dist_GM2.5_wrongROIbkdfpdf.dat' 
        #rslt_f_nm = 'data_output_new_data/RQs3386_10yrNu_TS_dist_GM2.5.dat' 
        #rslt_f_nm = 'data_output_new_data/RQs15Hz106_10yrNu_PDFs_WeightEq_GM2.5.dat' 
        
        rslt_f_nm = 'ttt.txt' 
        results = loadtxt(rslt_f_nm)
        print('# Number of srcs with ns_max>=0', len(where( results[:,3] >=0 )[0]) )
        
        #try: # Only for RQs
        results[:,2][ where(results[:,3]<0) ] *= -1
        idx = argsort( results[:,2] )[::-1]
    
        results = results[idx]
        #srcs_sorted = srcs[idx]
        
        tmp_TSs = results[:,2] 
        from scipy.stats import chi2
        ps_global  = 1. - chi2.cdf(tmp_TSs, 1)**N_src
        TSs_global = chi2.ppf(1-ps_global, 1) # inverse of cdf, to get global TS
        print(ps_global)
        print(TSs_global)
        
        tmp = concatenate( (results, 
            TSs_global.reshape(-1,1), 
            ps_global.reshape(-1,1), 
                            #srcs_sorted
                            ), axis=1 )
        savetxt( rslt_f_nm[0:-4]+'_sorted.txt', tmp, fmt='%s'  )
        
        del(tmp, tmp_TSs, idx)
        #except:
        #    pass
        
        # plot the TS distribution of all the sources.
        fig = plt.figure(figsize=(6, 6), facecolor='w')
        ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
        #[i.set_linewidth(1.5) for i in ax.spines.itervalues()] # default seems ~~0.8
        ax.set_xscale('linear'); ax.set_yscale('log')
        
        results = loadtxt(rslt_f_nm).T
        #print( where( results[3]>=0 )[0].shape )
        #exit()
        
        binss = arange(0., 10.+0.5,0.5) # 0.2 is the bin width used by the ppr
        tmp = results[2]
        tmp = sqrt(tmp[ where( results[3]>=0 ) ])
        print('Number of srcs with ns>=0, ', len(where(results[3]>=0)[0]) )
        Nums = histogram( tmp, binss)[0]
        bin_Cs = (binss[:-1] + binss[1:])/2.
        bin_err = ( binss[1]-binss[0] )/2.
        
        # Fit the TS dist with a gaussian
        plt.errorbar(bin_Cs, Nums, xerr=bin_err, yerr=sqrt(Nums), fmt ='bo', capsize=2,ms=4, label=r'Results from IceCube 10 yr data')
        
        # chi2 fit
        from lmfit.models import GaussianModel, ConstantModel
        idx = where(Nums>0)
        xval = bin_Cs[idx]; yval = Nums[idx]  
        err = sqrt(yval); weight = 1./err
        gauss = GaussianModel() # offset = ConstantModel()
        model = gauss # + offset
        # pars = offset.make_params(c=median(yval))
        # pars += gauss.guess(yval, x=xval, amplitude=-0.5)
        #pars = gauss.guess(yval, x=xval, amplitude=100., sigma=1, center=0)
        #pars = gauss.guess(yval, x=xval, amplitude=100., sigma=1, center=[0.,0.,0.])
        print(yval)
        print(xval)
        pars = gauss.guess(yval, x=xval, amplitude=100., sigma=1., center=0.)
        pars.add('center', value=0., min=0., max=0.01)
        pars.add('sigma', value=0., min=0.99, max=1.01)
        #exit()
        result = model.fit(yval, pars, x=xval, weights=weight) \
                # cheked by exactly reproducing the chi2 given by the fitting results, the weight is 1./err
        print(result.fit_report())
        print( result.redchi ) # https://lmfit.github.io/lmfit-py/fitting.html
        
        plt.plot(xval, result.best_fit, 'r--', label=r'Normal distribution fit, $\chi^2_{dof}='+str( round(result.redchi,2) )+'$')
        
        #ax.set_xlabel(r"$\sqrt{2\Delta {\rm ln} \mathcal{L}}$",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
        ax.set_xlabel(r"$\sqrt{\rm TS_{max}}$",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
        #ax.set_xlabel(r"$\sqrt{\rm TS_{max}}$  (Pre-trial)",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
        ax.set_ylabel(r"Number of sources in each bin",fontsize=20)
        ax.set_xlim(0,5)
        #use.autoscale_y(ax)
        ax.set_ylim(0.5,400)
        ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
        ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
        ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
        ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
        #plt.grid()#ls='-', lw=0.5)
        plt.savefig('figures/TS_dist.pdf',bbox_inches='tight', pad_inches=0.1)
        plt.show()
        exit()
    
'######################### !Single source analysis! ############################'


'#####################  ######################'
'#################### !! #####################'


'############################ Stacking analysis ###############################'
'# Weighting factors'
if IF_equal_weighting:
    W_facs = W_accs_src
else:
    W_facs = W_accs_src * W_mdls_src.reshape(1,-1)  \
        # (Nk, N_src)
        # For equal weighting, comment out the second term.
W_facs_normd = W_facs/( W_facs.sum(axis=1).reshape(-1,1) ) \
        #  (Nk, N_src) / (Nk, ) -> (Nk, N_src) weighted sumed
#print( W_facs_normd.sum(axis=1) )  # check if normalized

W_facs_sum = W_facs.sum(axis=1)/N_src \
        # Sum over srcs for each dataset, (Nk,)
        # This is used to calc fk
        # /N_src is actually not necessary; historical reason
fks = W_facs_sum/W_facs_sum.sum() 
print('# New fks', fks, ', compare with above #s' ) # old fks can be deleted later.

for i in range(0):  # plot something
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    #[i.set_linewidth(1.5) for i in ax.spines.itervalues()] # default seems ~~0.8
    ax.set_xscale('linear'); ax.set_yscale('log')
    #ax.set_xscale('linear'); ax.set_yscale('linear')
    
    ax.plot(Decs_src*d2r+90, W_facs_normd[0],'ro',label=r'IC79',lw=1.5,ms=1.) 
    ax.plot(Decs_src*d2r+90, W_facs_normd[1],'go',label=r'IC86a',lw=1.5,ms=1.) 
    ax.plot(Decs_src*d2r+90, W_facs_normd[2],'bo',label=r'IC86b',lw=1.5,ms=1.) 
    
    ax.set_xlabel(r"Zenith angle [ Degree ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    ax.set_ylabel(r"Relative $W_{\rm acc}$, $\Gamma$="+str(gamma),fontsize=20)
    ax.set_xlim(0,180)
    #use.autoscale_y(ax)
    ax.set_ylim(0,)
    ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    plt.grid()#ls='-', lw=0.5)
    plt.show()
    #plt.savefig('',,bbox_inches='tight', pad_inches=0.1)
    exit()

'##################### Tmp: Epdfs ######################'
B_E_pdfss = [ 
             loadtxt('data_output/Epdfs/bkgd_Epdf_IC40.txt'), 
             loadtxt('data_output/Epdfs/bkgd_Epdf_IC59.txt'), 
             loadtxt('data_output/Epdfs/bkgd_Epdf_IC79.txt'), 
             loadtxt('data_output/Epdfs/bkgd_Epdf_IC86a.txt'), 
             loadtxt('data_output/Epdfs/bkgd_Epdf_IC86b.txt'),  
             ]

S_E_pdfss = [
        loadtxt('data_output/Epdfs/signal_Epdf_2D_GM2.0_IC40.txt'),
        loadtxt('data_output/Epdfs/signal_Epdf_2D_GM2.0_IC59.txt'),
        loadtxt('data_output/Epdfs/signal_Epdf_2D_GM2.0_IC79.txt'),
        loadtxt('data_output/Epdfs/signal_Epdf_2D_GM2.0_IC86a.txt'),
        loadtxt('data_output/Epdfs/signal_Epdf_2D_GM2.0_IC86b.txt'),
        ]


'#################### !Tmp: Epdfs! #####################'


' ##### Calc the signal/bkgd PDFs for the joint llh !!!!!!!!!!!!!!!!!!!!! '
if IF_stacking_anlys_calc_PDFs:
    'For 2796 srcs, ~350k nus, only took 1m30s'
    S_ki = [];  B_ki = [] ; # Signal PDF # Background PDF
    for k in tqdm.tqdm( range( len(Nks) ) ):
        if k != 4:
            continue

        RAs_nu1D     = RAs_nu [k, 0:Nks[k]]
        Decs_nu1D    = Decs_nu[k, 0:Nks[k]]
        sgms_nu1D    = sgms_nu[k, 0:Nks[k]]
        lgEs_prxy_nu1D = lgEs_prxy_nu[k, 0:Nks[k]]
        
        B_E_pdfs = B_E_pdfss[k]
        S_E_pdfs = S_E_pdfss[k]

        S_sptl_ki1D = zeros(Nks[k])
        S_E_ki1D    = zeros(Nks[k])
        S_ki1D      = zeros(Nks[k])
        B_sptl_ki1D = zeros(Nks[k])
        B_E_ki1D    = zeros(Nks[k])
        B_ki1D      = zeros(Nks[k])

        #for i in tqdm.tqdm( range(Nks[k]) ): 
        for i in tqdm.tqdm( range(0) ): 
            'Later if confirmed using all-sky srcs, can easily change to 2D array.'
            RA_nu  = RAs_nu1D[i];  
            Dec_nu = Decs_nu1D[i];
            sgm_nu = sgms_nu1D[i];

            ang_dis = arccos( cos(RAs_src-RA_nu)*cos(Decs_src)*cos(Dec_nu) + sin(Decs_src)*sin(Dec_nu) )
            if isscalar(ang_dis): # for the case of only one src, wrap it in an array
                ang_dis = array([ang_dis])
        
            tmp_idx = where( ang_dis**2 < inf*sgm_nu**2. )  \
                    # 20250228, fogot why i did this, maybe i want to limit the distance betwee the srcs and the event. 
                    # Now i am using inf, so equivalent to removing this code block.
            ang_dis1 = ang_dis[tmp_idx]
            N_src1 = len(tmp_idx[0])
        
            if N_src1 > 0:
                spatial_facs = 1./(2.*pi*sgm_nu**2.)*exp( -(ang_dis1**2)/(2.*sgm_nu**2.) )
                S_sptl_ki1D[i] = sum(W_facs_normd[k]*spatial_facs)
            else:
                S_sptl_ki1D[i] = 0.
            tmp5 = bkgd_pdfs[k]
            B_sptl_ki1D[i] = tmp5( -sin( array([Dec_nu]) ) ) * Nks_tot[k]/Nks[k] \
                   # Rescale for a part of the sky. There is an issue for the 87 deg but the difference is negligible.

        iz = 0; # to adjust the mismatch between B_E_pdfs and the data used for LLH analysis; change to other variables later.
        i=0
        while 1:
            Dec_nu = Decs_nu1D[i];
            lgE_prxy = lgEs_prxy_nu1D[i];

            # Add E pdfs
            ##print()
            ##print( i+iz, B_E_pdfs[i+iz, 1:] )
            ##print( i,    Dec_nu*d2r, lgE_prxy )
            #if B_E_pdfs[i,1] == Dec_nu*d2r and B_E_pdfs[i,2]==lgE_prxy:
            if abs(use.rel_diff(B_E_pdfs[i+iz,1],Dec_nu*d2r)) < 1e-2 and abs(use.rel_diff(B_E_pdfs[i+iz,2],lgE_prxy))<1e-2:  ####!!!!
                B_E_ki1D[i] = B_E_pdfs[i+iz,3]  # cuz Col3 is the BEpdf for event i_
                ##print( B_E_ki1D[i] )
                i += 1
            else:
                ##print('# Mismatch! ')
                iz += 1
            if i == Decs_nu1D.size: # cuz there is  i+=1 in the end
                break

        # for S_E_pdf
        pdf2D = S_E_pdfs  # (1000, 801)
        coszs = linspace(-1, 1, 1000)
        Eprs  = use.ebs(1e1, 1e9, 8*100) # don't change, matches the file
        lgEprs = log10( Eprs )
        # Check if normalized; No need check actually, cuz already did when calculating
        #tmp = integrate.simps( pdf2D, lgEprs, axis=1 )
        #print('# Check if normalized', tmp )
        pdf2D_intp = intp.interp2d( lgEprs, coszs, pdf2D, bounds_error=True )
        
        ' calc E pdfs for events'
        coszs_ev  = -sin(Decs_nu1D)
        lgEprs_ev = lgEs_prxy_nu1D
        for i in range(Nks[k]): 
            S_E_ki1D[i] = pdf2D_intp(lgEprs_ev[i], coszs_ev[i])[0]
            #print(i, result)


        S_ki1D = S_sptl_ki1D * S_E_ki1D;
        B_ki1D = B_sptl_ki1D * B_E_ki1D;
        for i in range(Nks[k]): 
            print( i, N_src1, S_ki1D[i], B_ki1D[i], S_sptl_ki1D[i], B_sptl_ki1D[i], S_E_ki1D[i], B_E_ki1D[i] )
        ####S_ki = S_ki + [S_sptl_ki1D]; B_ki = B_ki + [B_sptl_ki1D]


def TS_tot(n_s):
    TS_tot = 0.
    n_s = float(n_s)
    # print( fks ); print( Nks1 ); print( S_ki ); print( B_ki ); exit()
    for k in range(len(Nks1)):
        # print( k, Nks1[k] )
        L_k  = n_s*fks[k]/float(Nks1[k])*S_ki[k] + (1.-n_s*fks[k]/float(Nks1[k]))*B_ki[k]
        L_k0 = B_ki[k]
        #print( L_k0 )
        #print( where(L_k0==0) )
        #exit()
        TS_k = 2.*sum( log(L_k) - log(L_k0) )
        TS_tot = TS_tot + TS_k
    return TS_tot

def max_TS_tot(ns0): # 
    def TS_tot1(n_s):
        return -1.*TS_tot(n_s)
    bnds = ( (-100., float( Nks1.sum() )), ) # has to have ',' here smh...
    res = minimize(TS_tot1, (ns0), bounds=bnds)  # method='SLSQP', 
    max_TS_j = -1*res.get('fun'); max_ns = res.get('x')[0];
    return max_TS_j, max_ns

def Delta_TS_tot_Not_using(Delta_TS): # 
    def TS_tot1(n_s):
        return abs( -1.*TS_tot(n_s) + Delta_TS )
    #bnds = ( (0., float( Nks1.sum() )), ) # has to have ',' here smh...
    bnds = ( (0., 1e5), ) # has to have ',' here smh...
    res = minimize(TS_tot1, (1280.), bounds=bnds)  # method='SLSQP', \
            # inital value not 0 to avoid finding the other min when TS_amx>0
    fitted_TS_j = -1*res.get('fun'); fitted_ns = res.get('x')[0];
    print( fitted_TS_j )
    #return fitted_TS_j+Delta_TS-TS_max, fitted_ns
    #return fitted_TS_j+Delta_TS-TS_max, fitted_ns
    return fitted_TS_j+Delta_TS, fitted_ns

def Delta_TS_tot(Delta_TS): # 
    from scipy.optimize import fsolve
    def TS_tot1(n_s):
        return TS_tot(n_s) - Delta_TS 
    root = fsolve(TS_tot1, 1280)
    #print( root )
    #print( TS_tot1(root) )
    return TS_tot(root), root[0]


' ##### Read the signal/bkgd PDFs for the joint llh !!!!!!!!!!!!!!!!!!!! '
if IF_stacking_anlys_calc_results:
    for i in range(1):  # 'Read the PDF data'
        if gamma == -2.00:
            gamma_str = '2.00'
        elif gamma == -2.53:
            gamma_str = '2.53'
        elif gamma == -3.00:
            gamma_str = '3.00'
        #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250221_SMBBHS_data_catalog_PDFs_WeightEq_GM'+gamma_str+'.txt').T
        #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250318_All_SMBBHs_data__PDFs_WeightDL_GM'+gamma_str+'.txt').T
        #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250404_All_SMBBHs_updated_data_693_PDFs_WeightEq_GM'+gamma_str+'.txt').T
        #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250404_All_SMBBHs_updated_data_335_PDFs_WeightEq_GM'+gamma_str+'.txt').T
        #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250404_All_SMBBHs_updated_data_468_PDFs_WeightEq_GM'+gamma_str+'.txt').T
        #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250404_All_SMBBHs_updated_data_693_PDFs_Weight1DL2_GM'+gamma_str+'.txt').T
        #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250404_All_SMBBHs_updated_data_335_PDFs_Weight1DL2_GM'+gamma_str+'.txt').T
        #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250404_All_SMBBHs_updated_data_468_PDFs_Weight1DL2_GM'+gamma_str+'.txt').T
        #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250404_All_SMBBHs_updated_data_335_PDFs_WeightLbolDL2_GM'+gamma_str+'.txt').T
        tmp = loadtxt('../20250221_SMBHB_Ranjan/data_output/20250404_All_SMBBHs_updated_data_335_PDFs_WeightNuFlux_GM'+gamma_str+'.txt').T
        
    
        # Signal pdf in col 2; B pdf in col 3.
        # Later make it a cycle
        B_pdf1 = tmp[3][ 0: Nks[0] ];
        S_pdf1 = tmp[2][ 0: Nks[0] ];
        idx = where( B_pdf1 > 0 );  # this is not needed actually
        B_pdf1 = B_pdf1[idx]; S_pdf1 = S_pdf1[idx]; Nks11 = len(idx[0])
        
        B_pdf2 = tmp[3][ Nks[0]: Nks[0]+Nks[1] ]
        S_pdf2 = tmp[2][ Nks[0]: Nks[0]+Nks[1] ]
        idx = where( B_pdf2 > 0 );
        B_pdf2 = B_pdf2[idx]; S_pdf2 = S_pdf2[idx]; Nks12 = len(idx[0])
        
        B_pdf3 = tmp[3][ Nks[0]+Nks[1]: Nks[0]+Nks[1]+Nks[2] ]
        S_pdf3 = tmp[2][ Nks[0]+Nks[1]: Nks[0]+Nks[1]+Nks[2] ]
        idx = where( B_pdf3 > 0 );
        B_pdf3 = B_pdf3[idx]; S_pdf3 = S_pdf3[idx]; Nks13 = len(idx[0])
        
        B_pdf4 = tmp[3][ Nks[0]+Nks[1]+Nks[2] : Nks[0]+Nks[1]+Nks[2]+Nks[3] ]
        S_pdf4 = tmp[2][ Nks[0]+Nks[1]+Nks[2] : Nks[0]+Nks[1]+Nks[2]+Nks[3] ]
        idx = where( B_pdf4 > 0 );
        B_pdf4 = B_pdf4[idx]; S_pdf4 = S_pdf4[idx]; Nks14 = len(idx[0])
    
        B_pdf5 = tmp[3][ Nks[0]+Nks[1]+Nks[2]+Nks[3] : Nks[0]+Nks[1]+Nks[2]+Nks[3]+Nks[4] ]
        S_pdf5 = tmp[2][ Nks[0]+Nks[1]+Nks[2]+Nks[3] : Nks[0]+Nks[1]+Nks[2]+Nks[3]+Nks[4] ]
        idx = where( B_pdf5 > 0 );
        B_pdf5 = B_pdf5[idx]; S_pdf5 = S_pdf5[idx]; Nks15 = len(idx[0])

        'Renormalize pdfs' # 
        for i5 in range(0):
            Decs_tmp = loadtxt('data_output/Decs_nu.txt')
            Decs1 = Decs_tmp[:,0][0:Nks[0]];
            Decs2 = Decs_tmp[:,1][0:Nks[1]];
            Decs3 = Decs_tmp[:,2][0:Nks[2]];
            Decs4 = Decs_tmp[:,3][0:Nks[3]];
            Decs5 = Decs_tmp[:,4][0:Nks[4]];

            sinDecs1 = sin(Decs1)
            sorted_indices = argsort(sinDecs1)
            sinDecs1 = sinDecs1[sorted_indices]
            B_pdf1a = B_pdf1[sorted_indices]
            norm = 2*pi*integrate.trapz(B_pdf1a, sinDecs1)
            print('norm', norm )
            B_pdf1 = B_pdf1/norm

            sinDecs2 = sin(Decs2)
            sorted_indices = argsort(sinDecs2)
            sinDecs2 = sinDecs2[sorted_indices]
            B_pdf2a = B_pdf2[sorted_indices]
            norm = 2*pi*integrate.trapz(B_pdf2a, sinDecs2)
            print('norm', norm )
            B_pdf2 = B_pdf2/norm

            sinDecs3 = sin(Decs3)
            sorted_indices = argsort(sinDecs3)
            sinDecs3 = sinDecs3[sorted_indices]
            B_pdf3a = B_pdf3[sorted_indices]
            norm = 2*pi*integrate.trapz(B_pdf3a, sinDecs3)
            print('norm', norm )
            B_pdf3 = B_pdf3/norm

            sinDecs4 = sin(Decs4)
            sorted_indices = argsort(sinDecs4)
            sinDecs4 = sinDecs4[sorted_indices]
            B_pdf4a = B_pdf4[sorted_indices]
            norm = 2*pi*integrate.trapz(B_pdf4a, sinDecs4)
            print('norm', norm )
            B_pdf4 = B_pdf4/norm

            sinDecs5 = sin(Decs5)
            sorted_indices = argsort(sinDecs5)
            sinDecs5 = sinDecs5[sorted_indices]
            B_pdf5a = B_pdf5[sorted_indices]
            norm = 2*pi*integrate.trapz(B_pdf5a, sinDecs5)
            print('norm', norm )
            B_pdf5 = B_pdf5/norm

            #exit()
        
        # I think here can control which dataset to use, plus revising fk
        S_ki = [ S_pdf1 , S_pdf2,  S_pdf3 , S_pdf4, S_pdf5 ]
        B_ki = [ B_pdf1 , B_pdf2,  B_pdf3 , B_pdf4, B_pdf5 ]
        Nks1 = array([ Nks11, Nks12, Nks13, Nks14, Nks15 ])
        print('#', fks )
        print('# For joint maxTS', Nks1 )
    
    # '''
    ns_s = use.ebs(1., 2000., 200) 
    TS_s = use.f2a( TS_tot, ns_s ) # ~5s
    ns_s_hat = ns_s[ argmax(TS_s) ]
    print('# Tentative ns_s_hat', ns_s_hat)
    #print('TS_s', TS_s)

    TS_max, ns_max = max_TS_tot(ns_s_hat)
    print('TS_max, ns_max: ', TS_max, ns_max)
    print( Delta_TS_tot( -3.84 ) ) 
    
    try:
        savetxt( flsvnm, array([ns_s, TS_s]).T )
    except:
        pass
    
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    #[i.set_linewidth(1.5) for i in ax.spines.itervalues()] # default seems ~~0.8
    #ax.set_xscale('linear'); ax.set_yscale('linear')
    ax.set_xscale('log'); ax.set_yscale('linear')
    
    ax.plot( ns_s, TS_s,'ro-',label=r'',lw=1.5,ms=2) 
    
    ax.plot( [1e-2, 1e5], [-3.84, -3.84],'k--',label=r'95%',lw=1.5,ms=2) 
    
    ax.plot( [8845.7*0.01, 8845.7*0.01], [-100, 10],'b--',label=r'$\sim 1\%$ of total astro nu flux',lw=1.5,ms=2) 
    
    #plt.errorbar(,,xerr = None,yerr =,fmt = 'bo',capsize=2,ms=4) 
    ax.set_xlabel(r"$n_s$",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    ax.set_ylabel(r'$-2 \Delta ln\mathcal{L}$',fontsize=20)
    ax.set_xlim(1,ns_s.max())
    #use.autoscale_y(ax)
    ax.set_ylim(TS_s.min()-1, TS_s.max()+10)
    ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    #plt.grid()#ls='-', lw=0.5)
    #plt.savefig('figures/TS_flux.pdf',bbox_inches='tight', pad_inches=0.1)
    plt.show()
    # '''

########################### !Stacking analysis! ##############################
