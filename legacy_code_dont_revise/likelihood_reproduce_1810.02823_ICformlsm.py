#!/usr/bin/python
import astropy.io.fits as pf
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
from scipy.optimize import minimize
import os,datetime
import use
set_printoptions(suppress=True, linewidth=10000, threshold=None)
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

# Some are copied from likelihood_reproduce_1810.02823.py

#####################################  ######################################
# Add Nsrc_i = zeros(N) # num of srcs assoc w/ the nu #######!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# or S_i[i] = -1e99
# Angular distance was wrong!!!!!!
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
Nus = loadtxt('data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/all_events.txt') # 138322 events.
# RAs in Nus[:,3]; Decs in Nus[:,4]; ang err in 2
#N = len(Nus) # 138322
sgm_nu = Nus[:,2]; Decs_nu = Nus[:,4];
#indx = where( (sgm_nu>0.)*(Decs_nu<87)*(Decs_nu>-87)*(sgm_nu<=10.) )[0];  #!
indx = where( (sgm_nu>0.)*(Decs_nu<87)*(Decs_nu>-87) )[0];  #!
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
#print AGNs[1448]


############################### Background PDF ################################
tmp = loadtxt('data_input/1601.06484_Fig9_right.dat').T

area = integrate.simps(tmp[1], tmp[0])
bkgd_pdf1 = intp.interp1d(tmp[0], tmp[1]/area/2./pi, kind='linear', bounds_error=False, fill_value=0) # correct

# from background_pdf.py, using Hooper's method
tmpNus = loadtxt('data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/all_events.txt') # 138322 events.
tmpDecs = tmpNus[:,4]/d2r; 

def bkgd_pdf_dec(dec):
    if dec > 87./d2r or dec < -87./d2r:
        return 0
    decLL = dec-3./d2r; decUL = dec+3./d2r;
    Omega = 2.*pi*( sin(decUL) - sin(decLL) )
    return len(where( (tmpDecs>decLL)*(tmpDecs<decUL) )[0])/Omega
def bkgd_pdf(cos_zenith):
    dec = arcsin( -cos_zenith )
    return use.f2a(bkgd_pdf_dec, dec)/21964.900815998473/2./pi # norm fac calcd below and 2pi
############################## !Background PDF! ###############################


S_i = zeros(N) # Signal PDF
B_i = zeros(N) # Background PDF

'''
for i in range(N): # only takes ~1m if use sgm_mu
    sgm_nu = Nus[i,2]/d2r
    RA_nu = Nus[i,3]/d2r; Dec_nu = Nus[i,4]/d2r;
    ang_dis = arccos( cos(RAs_AGN-RA_nu)*cos(Decs_AGN)*cos(Dec_nu) + sin(Decs_AGN)*sin(Dec_nu) )

    tmp_idx = where( ang_dis**2 < inf*sgm_nu**2. ) #!
    #print tmp_idx ###
    RAs_RQ1 = RAs_AGN[tmp_idx]; Decs_RQ1 = Decs_AGN[tmp_idx]; ang_dis1 = ang_dis[tmp_idx]
    N_src1 = len(tmp_idx[0]) 

    if N_src1 > 0:
        spatial_facs = 1./(2.*pi*sgm_nu**2.)*exp( -(ang_dis1**2)/(2.*sgm_nu**2.) )
        S_i[i] = 1./N_src1*spatial_facs.sum()  #! assuming w_acc and w_s are 1
    else:
        S_i[i] = 0.
    B_i[i] = bkgd_pdf( -sin( array([Dec_nu]) ) ) # For IceCube, cos(zenith) = -sin(Dec)
    print( i, N_src1, S_i[i], B_i[i] )
'''

def TS_tot(n_s):
    L_i = n_s/float(N)*S_i + (1.-n_s/float(N))*B_i
    L_i0 = B_i
    return 2.*sum( log( L_i/L_i0 ) )

def max_TS_tot(): # n_s can be any real number
    def TS_tot1(n_s):
        return -1.*TS_tot(n_s)
    bnds = ( (0., float(N)), ) # has to have ',' here smh...
    res = minimize(TS_tot1, (0.), bounds=bnds)  # method='SLSQP', 
    max_TS_j = -1*res.get('fun'); max_ns = res.get('x')[0];
    return max_TS_j, max_ns

tmp = loadtxt('data_output/ICform_PDFs_3.dat') #!
#tmp = tmp[ where( tmp[:,1]>0. )[0] ] #! 0.
#tmp = tmp[ where( tmp[:,1]>0. )[0] ] #! 0.
N = len(tmp); print( N ); # New N here!!! Change it to N1 later. #!
tmp = tmp.T

S_i = tmp[2]; B_i = tmp[3]

print( max_TS_tot() )

ns_s = use.ebs(1., 2000., 100) 
TS_s = use.f2a( TS_tot, ns_s ) # ~5s

fig = plt.figure(figsize=(6, 6), facecolor='w')
ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
#[i.set_linewidth(1.5) for i in ax.spines.itervalues()] # default seems ~~0.8
ax.set_xscale('log'); ax.set_yscale('linear')

ax.plot( ns_s, TS_s,'ro-',label=r'',lw=1.5,ms=2) 

#plt.errorbar(,,xerr = None,yerr =,fmt = 'bo',capsize=2,ms=4) 
ax.set_xlabel(r"$n_s$  [  ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
ax.set_ylabel(r"TS  [  ]",fontsize=20)
ax.set_xlim()
#use.autoscale_y(ax)
ax.set_ylim()
ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
plt.grid()#ls='-', lw=0.5)
plt.show()
