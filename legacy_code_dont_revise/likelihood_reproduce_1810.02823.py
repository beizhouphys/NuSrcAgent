#!/usr/bin/python
import astropy.io.fits as pf
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
from scipy.optimize import minimize
import os,datetime
import use
set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=3, floatmode='maxprec')

# Potential issues
'''
Might need check if different circles overlap
'''



#####################################  ######################################
#################################### !! #####################################
#####################################  ######################################
d2r = 180./pi
hbarc = 0.197326978 # GeVfm
sin2weakangle = 0.2223
alpha = 1/137.035999139; GF = 1.1663787e-5; e = 0.302822120811;
m_p = 0.93827231; m_n = 0.93956563; m_e = 0.5109906e-3; m_mu = 0.1056583745; m_tau = 1.77682
m_W = 80.385; m_Z = 91.1876
GeV2cm2 = 3.893793625E-28
#################################### !! #####################################

################################## Neutrinos ###################################
### likelihood_reproduce_1810.02823_ICformlsm.py is more updated here.
Nus = loadtxt('data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/all_events.txt') # 138322 events.
# RAs in Nus[:,3]; Decs in Nus[:,4]; ang err in 2
# There are 12 events have angular error 0. #!
#N = len(Nus) # 138322
sgm_nu = Nus[:,2]/d2r;
indx = where(sgm_nu > 0)[0]; #!
#indx = where( (sgm_nu>0.)*(sgm_nu<=10./d2r) )[0];  
Nus = Nus[indx]; N = len(Nus) 
RAs_nu = Nus[:,3]/d2r; Decs_nu = Nus[:,4]/d2r; sgm_nu = Nus[:,2]/d2r;
################################# !Neutrinos! ##################################

################################### Sources ####################################
tmp = loadtxt('data_input/3LAC.dat',dtype=str)
AGNs = array(tmp[:,0:7], dtype=float)
# Get the Decs in degree
deg     = array(AGNs[:,4], dtype=float)
minute  = array(AGNs[:,5], dtype=float); minute[where(deg < 0)] *= -1
sec     = array(AGNs[:,6], dtype=float); sec[where(deg < 0)] *= -1
Decs_AGN = deg + minute/60. + sec/3600. # checked the formula

AGNs = AGNs[ where( (Decs_AGN<87)*(Decs_AGN>-87) )[0] ]
N_src = len(AGNs) 
#print N_src  # 1769 correct!!
# Get the RAs and Decs in degree
hr     = array(AGNs[:,1], dtype=float)
minute = array(AGNs[:,2], dtype=float)
sec    = array(AGNs[:,3], dtype=float)
RAs_AGN = ( (hr + minute/60. + sec/3600.)/24.*360. )/d2r # checked the formula
deg     = array(AGNs[:,4], dtype=float)
minute  = array(AGNs[:,5], dtype=float); minute[where(deg < 0)] *= -1
sec     = array(AGNs[:,6], dtype=float); sec[where(deg < 0)] *= -1
Decs_AGN = ( deg + minute/60. + sec/3600. )/d2r # checked the formula
################################## !Sources! ###################################
#print( AGNs[1448] )
#exit()

#################################### Grid ######################################
for i in range(0):
    RAs_grid = arange(0.1, 359.9+0.2, 0.2)
    Decs_grid = arange(-87.+0.1, 87.-0.1+0.2, 0.2)
    # change things into radian later if use
    tmp1 = array( list(RAs_grid)*len(Decs_grid) )
    tmp2 = array( list(Decs_grid)*len(RAs_grid) )
    
    tmp1 = tmp1.reshape(len(Decs_grid), -1)
    tmp1 = tmp1.T
    tmp1 = tmp1.flatten()
    
    RAs_grid = tmp1
    Decs_grid = tmp2
    N_grid = len(RAs_grid) # 1566000
    
    for ii in range(0): # pre-select, takes ~45m,
        # Need use the same criteria as in logL_j() #!!!!!!!!!!!!!!!!!
        #for j2 in range(N):
        #    'Ruuning over neutrinos, still slow cuz too many grids'
        #    RA_nu2 = RAs_nu[j2]; Dec_nu2 = Decs_nu[j2];
        #    tmp_idx1 = where( ((RA_nu2-RAs_grid)>-0.1)*((RA_nu2-RAs_grid)<=0.1)*((Dec_nu2-Decs_grid)>-0.1)*((Dec_nu2-Decs_grid)<=0.1) ) [0]
        #    print j2, tmp_idx1
        
        for j1 in range(N_grid):
            RA_src = RAs_grid[j1]; Dec_src = Decs_grid[j1];
            tmp_idx = where( ((RAs_nu-RA_src)>=-0.1)*((RAs_nu-RA_src)<=0.1)*((Decs_nu-Dec_src)>=-0.1)*((Decs_nu-Dec_src)<=0.1) )  # This is not correct... I misunderstood what Hooper paper means...
            if len(tmp_idx[0]) > 0:
                print( j1, len(tmp_idx[0]) )
                # Printing RA/Dec gives numbers such as -78.89999999999989, which is problematic...
    #exit()
        
    tmp = loadtxt('data_output/Hooper_allsky_grids_1.dat', dtype=int).T # remember to change logL_j()!!!!!!!!!!
    RAs_grid =  RAs_grid[ tmp[0] ]; Decs_grid =  Decs_grid[ tmp[0] ]
    N_grid = len(RAs_grid) # 
    
    del tmp; del tmp1; del tmp2;
################################### !Grid! #####################################

############################### Background PDF ################################
tmp = loadtxt('data_input/1601.06484_Fig9_right.dat').T

area = integrate.simps(tmp[1], tmp[0])
bkgd_pdf1 = intp.interp1d(tmp[0], tmp[1]/area/2./pi, kind='linear', bounds_error=False, fill_value=0) # correct

# from background_pdf.py, using Hooper's method
tmpNus = loadtxt('data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/all_events.txt') # 138322 events.
tmpDecs = tmpNus[:,4]; tmpDecs = sort(tmpDecs) 

def bkgd_pdf_dec(dec):
    if dec > 87. or dec < -87.:
        return 0
    decLL = dec-3; decUL = dec+3;
    Omega = 2.*pi*( sin(decUL/d2r) - sin(decLL/d2r) )
    return len(where( (tmpDecs>decLL)*(tmpDecs<decUL) )[0])/Omega
def bkgd_pdf(cos_zenith):
    dec = arcsin( -cos_zenith )*d2r
    return use.f2a(bkgd_pdf_dec, dec)/21964.900815998473/2./pi # norm fac calcd below and 2pi
############################## !Background PDF! ###############################


#ROI = 100./d2r #! cicular ROI
ROI = 15./d2r # Dec band ROI
#ROI = 30./d2r # Dec band ROI
tmp7 = 0
def logL_j(j, n_s):
    print('Fix the ROI problem first, background pdf for 90-15 to 90 and -90+15 to -90!!!!!')
    exit()
    RA_src = RAs_AGN[j]; Dec_src = Decs_AGN[j]; #!
    #RA_src = RAs_grid[j]; Dec_src = Decs_grid[j];

    ang_dis = arccos( cos(RA_src-RAs_nu)*cos(Dec_src)*cos(Decs_nu) + sin(Dec_src)*sin(Decs_nu) )

    #tmp_idx = where( ang_dis**2 < ROI**2. ) #! circular ROI
    tmp_idx = where( abs( Dec_src-Decs_nu ) <= ROI ) #! Dec band ROI
    #tmp_idx = where( abs( Dec_src-Decs_nu ) <= 1e100 ) #! Full sky ROI
    RAs_nu1=RAs_nu[tmp_idx]; Decs_nu1=Decs_nu[tmp_idx]; sgm_nu1=sgm_nu[tmp_idx];
    ang_dis1 = ang_dis[tmp_idx]

    N1 = len(RAs_nu1); 
    if N1 == 0:
        return -999, N1
    spatial_facs = 1./(2.*pi*sgm_nu1**2.)*exp( -(ang_dis1**2)/(2.*sgm_nu1**2.) )
    S_ji = spatial_facs
    #B_i = ones(N1)/( 2.*pi*(1.-cos(ROI)) ) # for circular ROI #!
    B_i = ones(N1)/( 2.*pi*( sin(Dec_src+ROI) - sin(Dec_src-ROI) ) ) # for Dec band ROI
    #B_i = bkgd_pdf( -sin( array([Dec_src])/d2r) ) # Full sky ROI 
    #print( B_i )
    #exit()

    global tmp7
    if tmp7 == 0: # only need calc bkgdPDF once, which takes long time.
        pass
        #tmp6 = -sin( linspace(Dec_src-ROI, Dec_src+ROI, 10000) ) # For Dec band ROI, and compatible to large ROI  # this makes the running much slower
        #norm1 = -integrate.simps( bkgd_pdf(tmp6)*2.*pi, tmp6 ) 
        #    # norm to one  # sin(Dec) is from small to large, so cos(zenith) is from large to small, that's why need a "-" sign to make the norm1 positive.
        #B_i = bkgd_pdf( -sin( Decs_nu1 ) )/norm1
        #tmp7 = tmp7 + 1
    #print( B_i)

    L_ji = float(n_s)/float(N1)*S_ji + (1.-float(n_s)/float(N1))*B_i
    if L_ji.min() < 0:
        'To avoid log(0.) which happens when n_s < 0. Wont affect the results at all if not do this cuz the n_s < 0 srcs are thrown away.'
        return 1e99, N1
    logL_ji = log(L_ji)
    return logL_ji.sum(), N1

def TS_j(j, n_s):
    tmp3 = logL_j(j,n_s)[0]
    return 2.*( tmp3 - logL_j(j, 0.)[0] ) # code can be optimized here.

def max_TS_j1(j): # n_s can be any real number
    N1 = logL_j(j, 0.)[1]
    if N1 == 0:
        return -999, -999

    def TS_j1(n_s):
        return -TS_j(j, n_s)
    #bnds = ( (None, float(N1)), ) # has to have ',' here smh... #!
    #bnds = ( (0., float(N1)), ) # has to have ',' here smh... 
    bnds = ( (-20., float(N1)), ) 
        # has to have ',' here smh... # just pick a negative number as lower bound cuz if it's too small the L(n_s)/L(0) could overflow. The choice won't affect the results.
    res = minimize(TS_j1, (0.), method='SLSQP', bounds=bnds) 
    max_TS_j = -1*res.get('fun'); max_ns = res.get('x')[0];
    return array([N1, max_TS_j, max_ns])


def logL_j_4tot(j, n_s, Ntot): # done.
    'Copied from logL_j(); the changes are 1) N1->Ntot 2) Ntot is a var'
    RA_src = RAs_AGN[j]; Dec_src = Decs_AGN[j]; #!
    ang_dis = arccos( cos(RA_src-RAs_nu)*cos(Dec_src)*cos(Decs_nu) + sin(Dec_src)*sin(Decs_nu) )
    tmp_idx = where( abs( Dec_src-Decs_nu ) <= ROI ) #! Dec band ROI

    RAs_nu1=RAs_nu[tmp_idx]; Decs_nu1=Decs_nu[tmp_idx]; sgm_nu1=sgm_nu[tmp_idx];
    ang_dis1 = ang_dis[tmp_idx]
    tmpN1 = len(RAs_nu1); # global var
    if tmpN1 == 0:
        return -999, tmpN1
    spatial_facs = 1./(2.*pi*sgm_nu1**2.)*exp( -(ang_dis1**2.)/(2.*sgm_nu1**2.) )
    S_ji = spatial_facs
    B_i = ones(tmpN1)/( 2.*pi*( sin(Dec_src+ROI) - sin(Dec_src-ROI) ) ) # for Dec band ROI

    global tmp7
    if tmp7 == 0: # only need calc bkgdPDF once, which takes long time.
        pass
        #tmp6 = -sin( linspace(Dec_src-ROI, Dec_src+ROI, 10000) ) # For Dec band ROI, and compatible to large ROI  # this makes the running much slower
        #norm1 = -integrate.simps( bkgd_pdf(tmp6)*2.*pi, tmp6 )
        #    # norm to one  # sin(Dec) is from small to large, so cos(zenith) is from large to small, that's why need a "-" sign to make the norm1 positive.
        #B_i = bkgd_pdf( -sin( Decs_nu1 ) )/norm1
        #tmp7 = tmp7 + 1

    L_ji_4tot = float(n_s)/float(Ntot)*S_ji + (1.-float(n_s)/float(Ntot))*B_i
    logL_ji_4tot = log(L_ji_4tot)
    return logL_ji_4tot.sum(), tmpN1
# Joint likelihood, a dumb way...

def TS_tot(n_s): # not done yet.
    'If later used, need revise the code to match the other parts, including the three things to be fixed.'
    'A potential issue that L() gives 0. becuase its too small, solved in TS_j(). Deal with it when it happens.'
    TS_tot1 = 0.; 
    for j3 in range(N_src):
        tmp4 = logL_j_4tot(j3, 0., Ntot)
        if tmp4[1] > 0:
            tmp5 = logL_j_4tot(j3, float(n_s), Ntot)
            TS_tot1 = TS_tot1 + 2.*( tmp5[0]-tmp4[0] )
    return TS_tot1

# For joint L
Ntot = 0.
for j3 in range(N_src):
    RA_src = RAs_AGN[j3]; Dec_src = Decs_AGN[j3];
    tmp_idx2 = where( abs( Dec_src-Decs_nu ) <= ROI ) #! Dec band ROI
    Ntot = Ntot + len(tmp_idx2[0])
print( Ntot )  # 49586320.0
Ntot = 138310
n_ss = linspace(0, 4, 41)[1:]
#print( n_ss )
for ns_tmp in n_ss:
    print( ns_tmp, TS_tot(ns_tmp) )
exit()

# For single srcs with large TS.
#print( max_TS_j1(1486) ) # 1491 PKS_2322-488
#print( max_TS_j1(1448) )# 1453 RBS_1792
#print( max_TS_j1(1440) )# 1453 RBS_1792
#print( max_TS_j1(295) ) # PMN J0358+0629 
#print( max_TS_j1(684) ) # TXS 1013+054
#exit() ###

# For catelog
#for j1 in range(N_src):
#    tmp1 = max_TS_j1(j1)
#    print( array([j1, tmp1[0], tmp1[1], tmp1[2]]) )
#exit() ###



fig = plt.figure(figsize=(6, 6), facecolor='w')
ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
#[i.set_linewidth(1.5) for i in ax.spines.itervalues()] # default seems ~~0.8
ax.set_xscale('linear'); ax.set_yscale('log')

binss = arange(0., 6.+0.2,0.2) # 0.2 is the bin width used by the ppr
results = loadtxt('data_output/Hooper_likelihood_dst_srcs_4.dat').T
tmp = results[2]
tmp = sqrt(tmp[ where( results[3]>=0 ) ])
bins, edges = histogram( tmp, binss) 
left,right = edges[:-1],edges[1:] 
xx = array([left,right]).T.flatten()
yy = array([bins,bins]).T.flatten()
ax.plot(xx, yy,'-',label=r'BZ',lw=1.5,ms=2) 

#tmp = loadtxt('data_input/1810.02823_Fig3.dat').T
#ax.plot(tmp[0], tmp[1],'k-',label=r'Dan, Tim, Abby',lw=1.5,ms=2) 
tmp = loadtxt('data_input/1810.02823_Fig3_1.dat').T
plt.errorbar(tmp[0],tmp[1],xerr=None,yerr=sqrt(tmp[1]),fmt='ko',capsize=2,ms=4)


for i in range(0): # dist of grids
    binss = arange(0., 6.+0.1,0.1) # 0.1 is the bin width used by the ppr
    results = loadtxt('data_output/Hooper_allsky_grids_1_rslt.dat').T
    tmp = results[1]
    tmp = sqrt(tmp[ where( results[2]>=0 ) ])
    print( len(tmp) )
    exit()
    bins, edges = histogram( tmp, binss) 
    left,right = edges[:-1],edges[1:] 
    xx = array([left,right]).T.flatten()
    yy = array([bins,bins]).T.flatten()
    ax.plot(xx, yy,'-',label=r'all sky',lw=1.5,ms=2) 
    
    tmp = loadtxt('data_input/1810.02823_Fig1.dat').T
    ax.plot(tmp[0], tmp[1],'k-',label=r'Dan, Tim, Abby',lw=1.5,ms=2) 
    print( integrate.simps( tmp[1], tmp[0] ) )

ax.set_xlabel(r"$\sqrt{2\Delta {\rm ln} \mathcal{L}}$",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
#ax.set_ylabel(r"$E^2dN/dE$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
ax.set_xlim(0,)
use.autoscale_y(ax)
ax.set_ylim(0.9,)
ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
plt.grid()#ls='-', lw=0.5)
plt.show()
#plt.savefig('',,bbox_inches='tight', pad_inches=0.1)



#bkup
'''
def max_TS_j(j): # Only for n_s being an integer.
    N1 = logL_j(j, 0.)[1]
    #print N1
    if N1 == 0:
        return -999, -999

    max_TS_j = 0.; max_ns = 0;

    for i_ns in range(N1+1):
        tmp = TS_j(j, float(i_ns) )
        if max_TS_j < tmp:
            max_TS_j = tmp; max_ns = i_ns;
    return max_TS_j, max_ns

'''
