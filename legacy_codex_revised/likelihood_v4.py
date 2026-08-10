#!/usr/bin/python
import tqdm

'''
# Initally copied from likelihood_v3.py and modified the single source analysis part to accelerate.
# In this version I am going to revise the single src analysis code to make it faster, in order to run >1e6 simulations.
# In the modified version, S/B pdf are only calc'd once when maximizing the TS.  Only the single src analysis calc was changed.
'''

#####################################  ######################################
#################################### !! #####################################

from numpy import *
d2r = 180./pi

'################################### Input ####################################'
#gamma = -2.00; # cdx
gamma = -2.53; # cdx
#gamma = -3.00; # cdx

#IF_BKGD_PDF = True
#IF_stacking_anlys_calc_PDFs = True
IF_BKGD_PDF = False
IF_stacking_anlys_calc_PDFs = False # cdx

IF_equal_weighting = True # cdx
#IF_equal_weighting = False # cdx

' Need to compare the TS with the plot, cuz sometimes it cannot find the maximum. If not, change the value in line ~669, under function max_TS_tot_().'
#IF_single_src_anlys = True # cdx
IF_single_src_anlys = False # cdx

IF_stacking_anlys_calc_results = True # cdx
#IF_stacking_anlys_calc_results = False # cdx
IF_plot_fig4_reproduction = True # cdx
'################################## !Input! ###################################'

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
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC40_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC59_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC79_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC86_I_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC86_II2VII_exp_BZ.csv', # cdx
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
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC40_effectiveArea.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC59_effectiveArea.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC79_effectiveArea.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC86_I_effectiveArea.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC86_II_effectiveArea.csv', # cdx
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
'This block continues prev block.  So can put in the same file.'
'from background_pdf.py, using sliding window'
'Later make below to a cycle'

filenms = array([  # Donot use the neutrinos_data.py do calc the bkgd pdf, cuz the analysis region may be smaller than <87deg. # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC40_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC59_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC79_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC86_I_exp.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/events/uncorrected_probably/IC86_II2VII_exp_BZ.csv',]) # cdx

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
    bkgd_pdf_dir = './data_output/bkgd_pdfs_cdx' # cdx
    os.makedirs(bkgd_pdf_dir, exist_ok=True) # cdx
    bkgd_pdf_flms = array([ # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC40_exp_cdx.txt', # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC59_exp_cdx.txt', # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC79_exp_cdx.txt', # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC86_I_exp_cdx.txt', # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC86_II2VII_exp_BZ_cdx.txt',]) # cdx
    bkgd_pdfs_nu = [] # cdx
    for k in range(len(filenms)): # cdx
        bkgd_pdf_tmp = bkgd_pdfs[k]( -sin(Decs_nu[k, 0:Nks[k]]) ) # cdx
        bkgd_pdf_output = array([RAs_nu[k,0:Nks[k]]*d2r, Decs_nu[k,0:Nks[k]]*d2r, bkgd_pdf_tmp]).T # cdx
        savetxt(bkgd_pdf_flms[k], bkgd_pdf_output, fmt='%.12e', header='RA_deg Dec_deg bkgd_pdf_value') # cdx
        if len(bkgd_pdf_tmp) != Nks[k]: # cdx
            print('# Warning: bkgd pdf length mismatch', k, len(bkgd_pdf_tmp), Nks[k]) # cdx
        bkgd_pdfs_nu += [bkgd_pdf_tmp] # cdx
    
    
    for i in range(0): # cdx
        'Plot to check bkgd pdfs'
        fig = plt.figure(figsize=(6, 6), facecolor='w')
        ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
        ax.set_xscale('linear'); ax.set_yscale('linear')
        
        tmp8 = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 10000)
        #ax.plot(tmp8, bkgd_pdf2a(tmp8)*2*pi,'-',label=r'2',lw=1.5,ms=2) 
        #ax.plot(tmp8, bkgd_pdf3a(tmp8)*2*pi,'-',label=r'3',lw=1.5,ms=2) 
        #ax.plot(tmp8, bkgd_pdf4a(tmp8)*2*pi,'-',label=r'4',lw=1.5,ms=2) 
        
        lbls = ['IC40', 'IC59', 'IC79', 'IC86-I', 'IC86-II to IC86-VII'] # cdx
        for i in range(len(filenms)):
            #ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2) 
            ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=lbls[i],lw=1.5,ms=2) # cdx
        
        ax.set_xlim(-1,1); ax.set_ylim(0,1) # cdx
        ax.set_xlabel(r"$\cos$(zenith angle) or $-\sin$(Dec)",fontsize=20, labelpad=None) # cdx
        ax.set_ylabel(r"Background PDF",fontsize=20) # cdx
        ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
        ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
        ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
        ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
        plt.grid()#ls='-', lw=0.5)
        plt.savefig('figures/Fig2_background_pdf_cdx.pdf',bbox_inches='tight', pad_inches=0.1) # cdx
        exit()


if not IF_BKGD_PDF: # cdx
    bkgd_pdf_dir = './data_output/bkgd_pdfs_cdx' # cdx
    bkgd_pdf_flms = array([ # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC40_exp_cdx.txt', # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC59_exp_cdx.txt', # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC79_exp_cdx.txt', # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC86_I_exp_cdx.txt', # cdx
        bkgd_pdf_dir+'/bkgd_pdf_IC86_II2VII_exp_BZ_cdx.txt',]) # cdx
    bkgd_pdfs_nu = [] # cdx
    for k in range(len(filenms)): # cdx
        bkgd_pdf_tmp = loadtxt(bkgd_pdf_flms[k]) # cdx
        bkgd_pdfs_nu += [bkgd_pdf_tmp[:,2]] # cdx
 

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

        # The active ROI below is a declination band; prefilter before the angular-distance calculation.
        tmp_idx = where( abs( Dec_src-Decs_nu1D ) <= ROI ) # cdx
        RAs_nu1D1  = RAs_nu1D[tmp_idx]; # cdx
        Decs_nu1D1 = Decs_nu1D[tmp_idx]; # cdx
        sgms_nu1D1 = sgms_nu1D[tmp_idx]; # cdx

        ang_dis = cos(RA_src-RAs_nu1D1)*cos(Dec_src)*cos(Decs_nu1D1) + sin(Dec_src)*sin(Decs_nu1D1) # cdx
        ang_dis[ where(ang_dis<-1.) ] = -1.
        ang_dis[ where(ang_dis> 1.) ] = 1. \
                # Very low chance to have nums like -1.0000000027831957 in arccos() probably due to truncation error, which gives "RuntimeWarning: invalid value encountered in arccos". Won't change the rlst cuz the nu is so far from the src.  # Adding this slows the code...
        ang_dis = arccos( ang_dis ) 

        #tmp_idx = where( ang_dis**2 < ROI**2. ) # circular ROI
        ang_dis1 = ang_dis # cdx

        Njk = len(RAs_nu1D1); Nj += [Njk]
        spatial_facs = 1./(2.*pi*sgms_nu1D1**2.)*exp( -(ang_dis1**2)/(2.*sgms_nu1D1**2.) )
        S_jik = spatial_facs
        S_ji = S_ji + [S_jik]

        B_ik = bkgd_pdfs_nu[k][tmp_idx]*Nks[k]/Njk # better pdf # cdx
        # print('!!!!!!!!!!!! Check the code here next time using, due to the Bpdf normalization issue found ~20250303.')
        B_i += [B_ik]
    return S_ji, B_i, Nj

def logL_j(j, n_s): 
    logL_j = 0;
    for k in range( len(Nks) ):

        a = float( n_s*fks[k] )/float(Nj[k]) # cdx
        L_jik_fac = 1. + a*(SB_ji[k]-1.) # cdx
        if L_jik_fac.min() < 0:
            'To avoid log(0.) which happens when n_s < 0. Wont affect the results at all if not do this cuz the n_s < 0 srcs are thrown away.'
            return 1e99, Nj[k]
        logL_jik = logB_ki[k] + log(L_jik_fac).sum() # cdx

        logL_j = logL_j + logL_jik

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
    rslt_single_src_analys_table = [] # cdx
    N_src_trials = N_src # cdx
    for j1 in range(N_src):
        fks = W_accs_src[:,j1]/W_accs_src[:,j1].sum()  
        #print(fks)
        S_ji, B_i, Nj =  SnB_PDF(j1)
        SB_ji = [ S_ji[k]/B_i[k] for k in range(len(Nks)) ] # cdx
        logB_ki = [ log(B_i[k]).sum() for k in range(len(Nks)) ] # cdx
        tmp1 = max_TS_j1(j1)
        #print( j1, '  ', tmp1[0], '  ', tmp1[1], '  ', tmp1[2] )

        from scipy.stats import chi2
        dof=1.; p_loc   = chi2.sf(tmp1[1], dof)/2 # /2 bcuz degeneracy of a TS correspond to ns, one positive, the other negative.
        rslt_single_src_analys[j1] = array([ j1, tmp1[0], tmp1[1], tmp1[2], p_loc, RAs_src[j1]*d2r, Decs_src[j1]*d2r ])
        p_glob = 1. - (1. - p_loc)**N_src_trials # cdx
        s_loc = max(norm.isf(p_loc), 0.) # cdx
        s_glob = max(norm.isf(p_glob), 0.) # cdx
        rslt_single_src_analys_table += [[ # cdx
            j1, # cdx
            src_IVS_names[j1], # cdx
            src_J2000_names[j1], # cdx
            W_mdls_src[j1], # cdx
            tmp1[2], # cdx
            tmp1[1], # cdx
            p_loc, # cdx
            s_loc, # cdx
            p_glob, # cdx
            s_glob, # cdx
            RAs_src[j1]*d2r, # cdx
            Decs_src[j1]*d2r, # cdx
            tmp1[0], # cdx
        ]] # cdx
        if j1%100 == 0: print( j1, '  ', tmp1[0], '  ', tmp1[1], '  ', tmp1[2], '  ', p_loc, '  ', RAs_src[j1]*d2r, '  ', Decs_src[j1]*d2r  ) # cdx
        # index of src,  N of nus,        TS,         \hat{ns_}
    savetxt('ttt.txt', rslt_single_src_analys)
    rslt_single_src_analys_table = array(rslt_single_src_analys_table, dtype=object) # cdx
    idx_table = argsort(array(rslt_single_src_analys_table[:,5], dtype=float))[::-1] # cdx
    rslt_single_src_analys_table = rslt_single_src_analys_table[idx_table] # cdx
    hdr = 'rank index IVS_name J2000_name Xband_flux_Jy ns_hat TSmax pretrial_p pretrial_sigma posttrial_p posttrial_sigma RA_deg Dec_deg N_events_in_ROI' # cdx
    ranks = arange(1, N_src+1, dtype=int).reshape(-1,1) # cdx
    savetxt( # cdx
        'data_output/TableI_reproduction_five_sources_cdx.txt', # cdx
        concatenate((ranks, rslt_single_src_analys_table), axis=1), # cdx
        fmt='%s', # cdx
        header=hdr, # cdx
    ) # cdx
    savetxt( # cdx
        'data_output/TableI_reproduction_top5_cdx.txt', # cdx
        concatenate((ranks[:5], rslt_single_src_analys_table[:5]), axis=1), # cdx
        fmt='%s', # cdx
        header=hdr, # cdx
    ) # cdx
    
    for i in range(1): # process data and plot !!!!!!!!!!!!!!!!!!!!!! # cdx
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
        signed_TSs = results[:,2].copy()
        signed_TSs[ where(results[:,3]<0) ] *= -1
        idx = argsort( signed_TSs )[::-1]
    
        results = results[idx]
        signed_TSs = signed_TSs[idx]
        src_IVS_names_sorted = src_IVS_names[idx]
        src_J2000_names_sorted = src_J2000_names[idx]
        W_mdls_src_sorted = W_mdls_src[idx]
        
        tmp_TSs = results[:,2] 
        from scipy.stats import chi2
        ps_global  = 1. - (1. - results[:,4])**N_src
        sigs_local = norm.isf(results[:,4])
        sigs_global = norm.isf(ps_global)
        sigs_global[where(sigs_global<0)] = 0.
        print('# top five Table I-like rows:')
        for i_top in range(5):
            print(src_IVS_names_sorted[i_top], src_J2000_names_sorted[i_top], W_mdls_src_sorted[i_top], results[i_top,3], results[i_top,2], results[i_top,4], sigs_local[i_top], ps_global[i_top], sigs_global[i_top])
        
        table_rows = []
        for i_src in range(N_src):
            table_rows += [[
                src_IVS_names_sorted[i_src],
                src_J2000_names_sorted[i_src],
                W_mdls_src_sorted[i_src],
                results[i_src,3],
                results[i_src,2],
                signed_TSs[i_src],
                results[i_src,4],
                sigs_local[i_src],
                ps_global[i_src],
                sigs_global[i_src],
                results[i_src,5],
                results[i_src,6],
                int(results[i_src,0]),
                int(results[i_src,1]),
            ]]
        table_rows = array(table_rows, dtype=object)
        header = 'IVS_name J2000_name Xband_flux_Jy ns_hat TSmax signed_TS pretrial_p pretrial_sigma posttrial_p posttrial_sigma RA_deg Dec_deg source_index N_neutrinos_in_ROI'
        savetxt('data_output/TableI_all_sources_cdx.txt', table_rows, fmt='%s', header=header) # cdx
        savetxt('data_output/TableI_top5_cdx.txt', table_rows[:5], fmt='%s', header=header) # cdx
        
        del(table_rows, tmp_TSs, idx)
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
        
        binss = arange(0., 5.+0.25,0.25) # cdx
        tmp = results[2]
        tmp = sqrt(tmp[ where( results[3]>=0 ) ])
        print('Number of srcs with ns>=0, ', len(where(results[3]>=0)[0]) )
        Nums = histogram( tmp, binss)[0]
        bin_Cs = (binss[:-1] + binss[1:])/2.
        bin_err = ( binss[1]-binss[0] )/2.
        
        # Fit the TS dist with a gaussian
        plt.errorbar(bin_Cs, Nums, xerr=bin_err, yerr=sqrt(Nums), fmt ='bo', capsize=2,ms=4, label=r'Results from IceCube 10 yr data') # cdx
        
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
        
        plt.plot(xval, result.best_fit, 'r--', lw=2., label=r'Normal distribution fit, $\chi^2_{dof}='+str( round(result.redchi,2) )+'$') # cdx
        
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
        plt.savefig('figures/Fig3_TS_distribution_cdx.pdf',bbox_inches='tight', pad_inches=0.1) # cdx
        #plt.show()
        exit()
    
'######################### !Single source analysis! ############################'


    
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

stacking_output_dir = 'data_output/stacking_cdx' # cdx
os.makedirs(stacking_output_dir, exist_ok=True) # cdx
if gamma == -2.00: # cdx
    gamma_str = '2.00' # cdx
elif gamma == -2.53: # cdx
    gamma_str = '2.53' # cdx
elif gamma == -3.00: # cdx
    gamma_str = '3.00' # cdx
else: # cdx
    gamma_str = '%.2f' % abs(gamma) # cdx
if IF_equal_weighting: # cdx
    stacking_weight_str = 'WeightEq' # cdx
else: # cdx
    stacking_weight_str = 'WeightXband' # cdx
stacking_pdf_flnm = stacking_output_dir+'/RQs3386_10yrNu_PDFs_'+stacking_weight_str+'_GM'+gamma_str+'_cdx.txt' # cdx
stacking_ts_flnm = stacking_output_dir+'/RQs3386_10yrNu_TS_'+stacking_weight_str+'_GM'+gamma_str+'_cdx.txt' # cdx

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

' ##### Calc the signal/bkgd PDFs for the joint llh !!!!!!!!!!!!!!!!!!!!! '
if IF_stacking_anlys_calc_PDFs:
    'For 3386 srcs and 10 yr nus, calc in chunks and save the local PDFs.' # cdx
    S_ki = [];  B_ki = [] ; # Signal PDF # Background PDF
    stacking_rows = [] # cdx
    cos_Decs_src = cos(Decs_src) # cdx
    sin_Decs_src = sin(Decs_src) # cdx
    chunk_size = 512 # cdx
    for k in tqdm.tqdm( range( len(Nks) ) ):
        RAs_nu1D  = RAs_nu [k, 0:Nks[k]]
        Decs_nu1D = Decs_nu[k, 0:Nks[k]]
        sgms_nu1D = sgms_nu[k, 0:Nks[k]]

        S_ki1D = zeros(Nks[k])
        B_ki1D = bkgd_pdfs_nu[k] # cdx
        for i0 in tqdm.tqdm( range(0, Nks[k], chunk_size) ): # cdx
            i1 = min(i0+chunk_size, Nks[k]) # cdx
            RAs_nu2D  = RAs_nu1D[i0:i1].reshape(-1,1) # cdx
            Decs_nu2D = Decs_nu1D[i0:i1].reshape(-1,1) # cdx
            sgms_nu2D = sgms_nu1D[i0:i1].reshape(-1,1) # cdx
            cos_ang_dis = cos(RAs_src.reshape(1,-1)-RAs_nu2D)*cos_Decs_src.reshape(1,-1)*cos(Decs_nu2D) + sin_Decs_src.reshape(1,-1)*sin(Decs_nu2D) # cdx
            cos_ang_dis = clip(cos_ang_dis, -1., 1.) # cdx
            ang_dis2 = arccos(cos_ang_dis)**2. # cdx
            spatial_facs = 1./(2.*pi*sgms_nu2D**2.)*exp( -ang_dis2/(2.*sgms_nu2D**2.) ) # cdx
            S_ki1D[i0:i1] = dot(spatial_facs, W_facs_normd[k]) # cdx
        S_ki = S_ki + [S_ki1D]; B_ki = B_ki + [B_ki1D]
        stacking_rows += [array([ones(Nks[k])*k, RAs_nu1D*d2r, Decs_nu1D*d2r, S_ki1D, B_ki1D]).T] # cdx
    stacking_rows = concatenate(stacking_rows, axis=0) # cdx
    savetxt(stacking_pdf_flnm, stacking_rows, fmt='%.12e', header='sample_index RA_deg Dec_deg S_pdf B_pdf') # cdx
    print('# Saved stacking PDFs to', stacking_pdf_flnm) # cdx


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
    bnds = ( (0., float( Nks1.sum() )), ) # has to have ',' here smh... # cdx
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
        if not os.path.exists(stacking_pdf_flnm): # cdx
            print('# Missing stacking PDF file:', stacking_pdf_flnm) # cdx
            print('# Turn on IF_stacking_anlys_calc_PDFs for this gamma/weighting first.') # cdx
            exit() # cdx
        tmp = loadtxt(stacking_pdf_flnm).T # cdx
        
    
        # Signal pdf in col 3; B pdf in col 4 for local stacking files. # cdx
        # Later make it a cycle
        B_pdf1 = tmp[4][ 0: Nks[0] ]; # cdx
        S_pdf1 = tmp[3][ 0: Nks[0] ]; # cdx
        idx = where( B_pdf1 > 0 );  # this is not needed actually
        B_pdf1 = B_pdf1[idx]; S_pdf1 = S_pdf1[idx]; Nks11 = len(idx[0])
        
        B_pdf2 = tmp[4][ Nks[0]: Nks[0]+Nks[1] ] # cdx
        S_pdf2 = tmp[3][ Nks[0]: Nks[0]+Nks[1] ] # cdx
        idx = where( B_pdf2 > 0 );
        B_pdf2 = B_pdf2[idx]; S_pdf2 = S_pdf2[idx]; Nks12 = len(idx[0])
        
        B_pdf3 = tmp[4][ Nks[0]+Nks[1]: Nks[0]+Nks[1]+Nks[2] ] # cdx
        S_pdf3 = tmp[3][ Nks[0]+Nks[1]: Nks[0]+Nks[1]+Nks[2] ] # cdx
        idx = where( B_pdf3 > 0 );
        B_pdf3 = B_pdf3[idx]; S_pdf3 = S_pdf3[idx]; Nks13 = len(idx[0])
        
        B_pdf4 = tmp[4][ Nks[0]+Nks[1]+Nks[2] : Nks[0]+Nks[1]+Nks[2]+Nks[3] ] # cdx
        S_pdf4 = tmp[3][ Nks[0]+Nks[1]+Nks[2] : Nks[0]+Nks[1]+Nks[2]+Nks[3] ] # cdx
        idx = where( B_pdf4 > 0 );
        B_pdf4 = B_pdf4[idx]; S_pdf4 = S_pdf4[idx]; Nks14 = len(idx[0])
    
        B_pdf5 = tmp[4][ Nks[0]+Nks[1]+Nks[2]+Nks[3] : Nks[0]+Nks[1]+Nks[2]+Nks[3]+Nks[4] ] # cdx
        S_pdf5 = tmp[3][ Nks[0]+Nks[1]+Nks[2]+Nks[3] : Nks[0]+Nks[1]+Nks[2]+Nks[3]+Nks[4] ] # cdx
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
    if TS_max <= 0.: # cdx
        TS_max = 0. # cdx
        ns_max = 0. # cdx
    print('TS_max, ns_max: ', TS_max, ns_max)
    TS_s = TS_s - TS_max # cdx
    def TS_tot_rel(n_s): # cdx
        return TS_tot(n_s)-TS_max+3.84 # cdx
    from scipy.optimize import brentq # cdx
    ns_hi = max(10., ns_max+10.) # cdx
    while TS_tot_rel(ns_hi) > 0. and ns_hi < Nks1.sum(): # cdx
        ns_hi *= 2. # cdx
    try: # cdx
        ns_95 = brentq(TS_tot_rel, max(ns_max, 0.), ns_hi) # cdx
        print('# ns_95:', ns_95) # cdx
    except: # cdx
        ns_95 = nan # cdx
        print('# Could not find ns_95 root.') # cdx
    
    try:
        savetxt( stacking_ts_flnm, array([ns_s, TS_s]).T, header='ns TS_minus_TSmax') # cdx
        print('# Saved stacking TS curve to', stacking_ts_flnm) # cdx
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
    plt.savefig('figures/TS_flux_'+stacking_weight_str+'_GM'+gamma_str+'_cdx.pdf',bbox_inches='tight', pad_inches=0.1) # cdx
    #plt.show() # cdx
    # '''


def stacking_ts_curve_file(weight_tag, gm_tag): # cdx
    return stacking_output_dir+'/RQs3386_10yrNu_TS_'+weight_tag+'_GM'+gm_tag+'_cdx.txt' # cdx


def ns_to_flux100_fig4(ns, gm_tag): # cdx
    gamma_val = -float(gm_tag) # cdx
    astro_ns_refs = {-2.00: 3217.3, -2.53: 8845.7, -3.00: 49282.2} # cdx
    phi0_mu = {-2.00: 5e-18/3., -2.53: 1.66e-18, -3.00: 5e-18/3.} # cdx
    astro_flux100 = 3.*phi0_mu[gamma_val]*1e10 # cdx
    return ns/astro_ns_refs[gamma_val]*astro_flux100 # cdx


def ns95_from_ts_curve(ns_s1, TS_s1): # cdx
    target = -3.84 # cdx
    diff = TS_s1-target # cdx
    idx = where(diff[:-1]*diff[1:] <= 0.)[0] # cdx
    if len(idx) == 0: # cdx
        return nan # cdx
    i = idx[0] # cdx
    return ns_s1[i] + (target-TS_s1[i])*(ns_s1[i+1]-ns_s1[i])/(TS_s1[i+1]-TS_s1[i]) # cdx


def setup_fig4_axes(ax): # cdx
    ax.tick_params(axis='both', which='major', direction='in', length=10, width=1.4, labelsize=18, top=True, right=True) # cdx
    ax.tick_params(axis='both', which='minor', direction='in', length=5, width=1.0, labelsize=18, top=True, right=True) # cdx
    for spine in ax.spines.values(): # cdx
        spine.set_linewidth(1.1) # cdx


def plot_fig4_reproduction_from_stacking_outputs(): # cdx
    gm_tags = ['2.00', '2.53', '3.00'] # cdx
    weight_rows = [('WeightEq', 'Equal weighting', 'red'), ('WeightXband', 'X-band flux-density weighting', 'blue')] # cdx
    linestyles = {'2.00': '--', '2.53': '-', '3.00': '-.'} # cdx
    gamma_labels = {'2.00': '-2.0', '2.53': '-2.53', '3.00': '-3.0'} # cdx
    missing = [] # cdx
    for weight_tag, label, color in weight_rows: # cdx
        for gm_tag in gm_tags: # cdx
            if not os.path.exists(stacking_ts_curve_file(weight_tag, gm_tag)): # cdx
                missing.append(stacking_ts_curve_file(weight_tag, gm_tag)) # cdx
    if len(missing) > 0: # cdx
        print('# Missing TS files for Fig. 4 reproduction:') # cdx
        for flm in missing: # cdx
            print('#', flm) # cdx
        return # cdx

    ns95 = {} # cdx
    fig = plt.figure(figsize=(6.2, 6.2), facecolor='w') # cdx
    ax = fig.add_axes([0.15, 0.13, 0.80, 0.82]) # cdx
    ax.set_xscale('log'); ax.set_yscale('linear') # cdx
    handles = [] # cdx
    for weight_tag, label, color in weight_rows: # cdx
        for gm_tag in gm_tags: # cdx
            ns_s1, TS_s1 = loadtxt(stacking_ts_curve_file(weight_tag, gm_tag)).T # cdx
            ns95[(weight_tag, gm_tag)] = ns95_from_ts_curve(ns_s1, TS_s1) # cdx
            flux_s1 = ns_to_flux100_fig4(ns_s1, gm_tag) # cdx
            line, = ax.plot(flux_s1, TS_s1, color=color, ls=linestyles[gm_tag], lw=2.0) # cdx
            if gm_tag == '2.53': # cdx
                handles.append(line) # cdx
    astro_center = 3.*1.66e-18*1e10 # cdx
    ax.axhline(-3.84, color='k', ls='--', lw=1.8) # cdx
    ax.axvspan(astro_center*0.78, astro_center*1.22, color='mediumseagreen', alpha=0.65, ec='green', lw=1.5) # cdx
    ax.axvline(astro_center, color='green', lw=2.0) # cdx
    ax.annotate(r'95\% limit', xy=(3.1e-10, -3.84), xytext=(6.3e-11, -3.72), fontsize=18, color='k', arrowprops=dict(arrowstyle='-|>', color='k', lw=1.5)) # cdx
    ax.text(3.6e-8, 0.78, 'Tot. astroph. $\\nu$ flux at 100 TeV\n(IceCube)', color='green', fontsize=18, ha='right', va='top') # cdx
    ax.text(1.5e-8, -2.35, gamma_labels['2.00'], color='red', fontsize=18) # cdx
    ax.text(2.1e-9, -2.35, gamma_labels['2.53'], color='red', fontsize=18) # cdx
    ax.text(4.0e-10, -2.35, gamma_labels['3.00'], color='red', fontsize=18) # cdx
    ax.text(8.0e-9, -5.25, gamma_labels['2.00'], color='blue', fontsize=18) # cdx
    ax.text(1.2e-9, -5.25, gamma_labels['2.53'], color='blue', fontsize=18) # cdx
    ax.text(1.3e-10, -5.25, r'$\Gamma=-3.0$', color='blue', fontsize=18) # cdx
    ax.set_xlabel(r'$E_\nu^2 dF_\nu/dE_\nu$ at 100 TeV  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]', fontsize=20) # cdx
    ax.set_ylabel('TS', fontsize=22) # cdx
    ax.set_xlim(5e-11, 1e-7); ax.set_ylim(-10, 1) # cdx
    ax.legend(handles, [weight_rows[0][1], weight_rows[1][1]], loc='lower left', fontsize=16, framealpha=0.80) # cdx
    setup_fig4_axes(ax) # cdx
    plt.savefig('figures/Fig4_left_panel_reproduction_cdx.pdf', bbox_inches='tight', pad_inches=0.06) # cdx
    plt.savefig('figures/Fig4_left_panel_reproduction_cdx.png', dpi=240, bbox_inches='tight', pad_inches=0.06) # cdx
    plt.close(fig) # cdx

    fig = plt.figure(figsize=(6.2, 6.2), facecolor='w') # cdx
    ax = fig.add_axes([0.16, 0.13, 0.79, 0.82]) # cdx
    ax.set_xscale('log'); ax.set_yscale('log') # cdx
    Es = use.ebs(1e3, 1e7, 500) # cdx
    handles = [] # cdx
    for weight_tag, label, color in weight_rows: # cdx
        for gm_tag in gm_tags: # cdx
            flux100 = ns_to_flux100_fig4(ns95[(weight_tag, gm_tag)], gm_tag) # cdx
            gamma_val = -float(gm_tag) # cdx
            yy = flux100*(Es/1e5)**(gamma_val+2.) # cdx
            line, = ax.plot(Es, yy, color=color, ls=linestyles[gm_tag], lw=2.0) # cdx
            if gm_tag == '2.53': # cdx
                handles.append(line) # cdx
    center = astro_center*(Es/1e5)**(-0.53) # cdx
    ax.fill_between(Es, center*0.78, center*1.22, color='mediumseagreen', alpha=0.65, ec='green', lw=1.3) # cdx
    ax.plot(Es, center, color='green', lw=2.0) # cdx
    for weight_tag, color, x1, x2 in [('WeightEq', 'red', 4.5e5, 1.5e6), ('WeightXband', 'blue', 3.0e5, 1.0e6)]: # cdx
        y = ns_to_flux100_fig4(ns95[(weight_tag, '2.00')], '2.00') # cdx
        ax.hlines(y, 1e3, 1e7, colors=color, linestyles='--', lw=1.6) # cdx
        ax.annotate('', xy=(x1, y/2.0), xytext=(x1, y), arrowprops=dict(arrowstyle='-|>', color=color, lw=1.5)) # cdx
        ax.annotate('', xy=(x2, y/8.0), xytext=(x2, y/3.0), arrowprops=dict(arrowstyle='-|>', color=color, lw=1.5)) # cdx
    ax.text(1.4e5, 1.3e-8, gamma_labels['2.00'], color='red', fontsize=18) # cdx
    ax.text(1.7e6, 1.0e-9, gamma_labels['2.53'], color='red', fontsize=18, rotation=-32) # cdx
    ax.text(1.9e5, 4.5e-10, gamma_labels['3.00'], color='red', fontsize=18) # cdx
    ax.text(7.0e4, 7.0e-9, gamma_labels['2.00'], color='blue', fontsize=18) # cdx
    ax.text(6.8e5, 7.0e-10, gamma_labels['2.53'], color='blue', fontsize=18, rotation=-32) # cdx
    ax.text(2.3e4, 2.6e-10, r'$\Gamma=-3.0$', color='blue', fontsize=18) # cdx
    ax.text(1.6e4, 2.4e-7, 'Tot. astroph. $\\nu$ flux (IceCube)', color='green', fontsize=18, rotation=-28, ha='left', va='top') # cdx
    ax.set_xlabel(r'$E_\nu$  [ GeV ]', fontsize=20) # cdx
    ax.set_ylabel(r'$E_\nu^2 dF_\nu/dE_\nu$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]', fontsize=20) # cdx
    ax.set_xlim(1e3, 1e7); ax.set_ylim(4e-11, 3e-7) # cdx
    ax.legend(handles, [weight_rows[0][1], weight_rows[1][1]], loc='lower left', fontsize=16, framealpha=0.80) # cdx
    setup_fig4_axes(ax) # cdx
    plt.savefig('figures/Fig4_right_panel_reproduction_cdx.pdf', bbox_inches='tight', pad_inches=0.06) # cdx
    plt.savefig('figures/Fig4_right_panel_reproduction_cdx.png', dpi=240, bbox_inches='tight', pad_inches=0.06) # cdx
    plt.close(fig) # cdx
    print('# Saved Fig. 4 reproduction panels to figures/.') # cdx


if IF_plot_fig4_reproduction: # cdx
    plot_fig4_reproduction_from_stacking_outputs() # cdx

########################### !Stacking analysis! ##############################
