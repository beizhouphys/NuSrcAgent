#!/usr/bin/python
# -*- coding:utf-8 -*- 
import astropy.io.fits as pf
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
import os,datetime
import use
# set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=3, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

#####################################  ######################################
#################################### !! #####################################
d2r = 180./pi
hbarc = 0.197326978 # GeVfm
sin2weakangle = 0.2223
alpha = 1/137.035999139; GF = 1.1663787e-5; e = 0.302822120811;
m_p = 0.93827231; m_n = 0.93956563; m_e = 0.5109906e-3; m_mu = 0.1056583745; m_tau = 1.77682
m_W = 80.385; m_Z = 91.1876
GeV2cm2 = 3.893793625E-28


# bkgd pdf
for i in range(0): # in Dec
    'Plot to check bkgd pdfs'
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('linear')
    
    tmp8 = linspace( cos((87.+90.)/d2r), cos((-87.+90.)/d2r), 100+1)
    #ax.plot(tmp8, bkgd_pdf2a(tmp8)*2*pi,'-',label=r'2',lw=1.5,ms=2) #!
    #ax.plot(tmp8, bkgd_pdf3a(tmp8)*2*pi,'-',label=r'3',lw=1.5,ms=2) #!
    #ax.plot(tmp8, bkgd_pdf4a(tmp8)*2*pi,'-',label=r'4',lw=1.5,ms=2) #!
    
    i = 0
    #ax.plot(tmp8, bkgd_pdfs[i](tmp8)*2*pi,'-',label=r''+str(i),lw=1.5,ms=2)
    #savetxt('data_output_new_data/bkgdpdf_cosz_IC40_101.txt', array([tmp8, bkgd_pdfs[i](tmp8)]).T )
    tmp8 = loadtxt('data_output_new_data/bkgdpdf_cosz_IC40_101.txt').T
    ax.plot(tmp8[0], tmp8[1]*2*pi,'m-',label=r'',lw=1.5,ms=2)
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
    #plt.savefig('./Tex_20201030_HEnu_radio_quasars/bkgd_pdf.pdf',bbox_inches='tight', pad_inches=0.1)
    plt.show()
    exit()



# TS v.s. ns
# '''
fig = plt.figure(figsize=(6, 6), facecolor='w')
ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
#[i.set_linewidth(1.5) for i in ax.spines.itervalues()] # default seems ~~0.8
ax.set_xscale('log'); ax.set_yscale('linear')

tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightEq_GM2.53.dat').T
ax.plot(tmp[0],tmp[1],'r-',label=r'Equal Weighting, $\Gamma=-2.53$',lw=1.5,ms=2)
tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightEq_GM2.15.dat').T
ax.plot(tmp[0],tmp[1],'r--',label=r'Equal Weighting, $\Gamma=-2.15$',lw=1.5,ms=2)
#tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightEq_GM2.28.dat').T
#ax.plot(tmp[0],tmp[1],'r--',label=r'Equal Weighting, $\Gamma=-2.28$',lw=1.5,ms=2)
tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightEq_GM3.0.dat').T
ax.plot(tmp[0],tmp[1],'r-.',label=r'Equal Weighting, $\Gamma=-3.0$',lw=1.5,ms=2)

tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightXFlux_GM2.53.dat').T
ax.plot(tmp[0], tmp[1],'b-',label=r'8 GHz flux Weighting, $\Gamma=-2.53$',lw=1.5,ms=2) 
tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightXFlux_GM2.0.dat').T
ax.plot(tmp[0], tmp[1],'b--',label=r'8 GHz flux Weighting, $\Gamma=-2.0$',lw=1.5,ms=2) 
#tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightXFlux_GM2.28.dat').T
#ax.plot(tmp[0], tmp[1],'b--',label=r'8 GHz flux Weighting, $\Gamma=-2.28$',lw=1.5,ms=2) 
tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightXFlux_GM3.0.dat').T
ax.plot(tmp[0], tmp[1],'b-.',label=r'8 GHz flux Weighting, $\Gamma=-3.0$',lw=1.5,ms=2) 

ax.plot( [1e-2, 1e5], [-3.84, -3.84],'k--',label=r'',lw=1.5,ms=2)

ax.plot( [8845.7*0.1, 8845.7*0.1], [-100, 10],'g--',label=r'',lw=1.5,ms=2)


ax.text(1e1, -3.73, r'$95\%$ limit', color='k', size=18, rotation = 0)
ax.text(7,  1.35, r'Tot astroph. $\nu$ flux $\times 10\%$', color='g', size=18, rotation = 0)


#plt.errorbar(,,xerr = None,yerr =,fmt = 'bo',capsize=2,ms=4)
ax.set_xlabel(r"$n_s$",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
ax.set_ylabel(r"$\Delta$TS",fontsize=20)
ax.set_xlim(1,1e4)
#use.autoscale_y(ax)
ax.set_ylim(-10,2)
ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
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

    #locmaj_y = matplotlib.ticker.LogLocator(base=10.0, subs=(1.0, ), numticks=100)
    #locmin_y = matplotlib.ticker.LogLocator(base=10.0, subs=arange(2, 10) * .1,
    #        numticks=100)
    #ax.yaxis.set_major_locator(locmaj_y)
    #ax.yaxis.set_minor_locator(locmin_y)
    #ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
#plt.grid()#ls='-', lw=0.5)
#plt.savefig('figures/TS_ns.pdf',bbox_inches='tight', pad_inches=0.1)
plt.show()
# '''


# TS v.s. Flux
'''

fig = plt.figure(figsize=(6, 6), facecolor='w')
ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
#[i.set_linewidth(1.5) for i in ax.spines.itervalues()] # default seems ~~0.8
ax.set_xscale('log'); ax.set_yscale('linear')

def dIdEnu0(Enus): # -2.53
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    'Use the measured results by IC coll, in 2001.09520'
    return 1.66e-18*(Enus/1e5)**(-2.53)*3 
def dIdEnu1(Enus): # -2.
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.)*3 
def dIdEnu3(Enus): # -2.28
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.28)*3 
def dIdEnu2(Enus): # -3.
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-3.)*3 
def dIdEnuX(Enus): # -2.X # hardest spec allowed for the Eq weighting
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.15)*3 


idx = 2;
E0 = 1e5;

##tmp = loadtxt('./data_input/2001.09520_fig3_astro_flux_C.dat').T
##ax.plot(tmp[0], tmp[1],'b--',label=r'',lw=1.5,ms=2) 
#tmp1 = loadtxt('./data_input/2001.09520_fig3_astro_flux_U.dat').T
#ax.plot(tmp1[0], tmp1[1]*3,'g-',label=r'',lw=1.5,ms=2) 
#tmp2 = loadtxt('./data_input/2001.09520_fig3_astro_flux_L.dat').T
#ax.plot(tmp2[0], tmp2[1]*3,'g-',label=r'',lw=1.5,ms=2) 
#xxs, yys = use.org_data( [tmp1[0],tmp2[0]],[tmp1[1]*3,tmp2[1]*3], fill_value_='extrapolate', nlogbins=1000  )
#
#ax.plot( [ dIdEnu0(3e4)*3e4**2 , dIdEnu0(3e4)*3e4**2 ], [-100, 10],'g--',label=r'',lw=1.5,ms=2) # checked with Hooper figure
ax.plot( [ dIdEnu0(E0)*E0**2 , dIdEnu0(E0)*E0**2 ], [-100, 10],'g-',label=r'',lw=1.5,ms=2) # checked
ax.plot( [ 3.83e-8 , 3.83e-8 ], [-100, 10],'g-',label=r'',lw=1.5,ms=2) \
        # checked # LL
ax.plot( [ 6.165e-8 , 6.165e-8 ], [-100, 10],'g-',label=r'',lw=1.5,ms=2) \
        # checked # UL
ax.axvspan(3.83e-8, 6.165e-8, alpha=1, color='#6dd4b2')

tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightEq_GM2.0.dat').T
ax.plot(tmp[0]/3281.23*dIdEnuX(E0)*E0**idx, tmp[1],'r--',label=r'',lw=1.5,ms=2)
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 3281.23*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV

tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightEq_GM2.53.dat').T
ax.plot(tmp[0]/8845.71*dIdEnu0(E0)*E0**idx, tmp[1],'r-',label=r'Equal weighting',lw=1.5,ms=2) # 4.98 = 3*1.66
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 8845.71*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV

tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightEq_GM3.0.dat').T
ax.plot(tmp[0]/49250.3*dIdEnu2(E0)*E0**idx, tmp[1],'r-.',label=r'',lw=1.5,ms=2)
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 49250.3*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV


tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightXFlux_GM2.0.dat').T
ax.plot(tmp[0]/3281.23*dIdEnu1(E0)*E0**idx, tmp[1],'b--',label=r'',lw=1.5,ms=2) 
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 3281.23*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV

tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightXFlux_GM2.53.dat').T
ax.plot(tmp[0]/8845.71*dIdEnu0(E0)*E0**idx, tmp[1],'b-',label=r'X-band flux-density weighting',lw=1.5,ms=2) 
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 8845.71*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV

tmp = loadtxt('data_output_new_data/RQs3386_10yrNu_TSns_WeightXFlux_GM3.0.dat').T
ax.plot(tmp[0]/49250.32*dIdEnu2(E0)*E0**idx, tmp[1],'b-.',label=r'',lw=1.5,ms=2) 
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 49250.32*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV


ax.text(2.9e-10,  0.45, r'Tot. astroph. $\nu$ flux at 100 TeV', color='g', size=18, rotation = 0)
ax.text(7.25e-9,  -0.1, r'(IceCube)', color='g', size=18, rotation = 0)
ax.plot( [1e-12, 1e-7], [-3.84, -3.84],'k--',label=r'',lw=1.7,ms=2)
ax.text( 0.6e-10, -3.73, r'$95\%$ limit', color='k', size=18, rotation = 0)
ax.annotate('', xytext=(3.07e-10, -3.84), 
                    xy=(3.07e-10, -3),
        arrowprops=dict(color='k', width=0.8, headwidth=4, headlength=8, shrink=0.01),)

for i in range(0):
    ax.text(1.38e-10, -4.8, r'$\Gamma$ = -3.0', color='b', size=18, rotation = 0)
    ax.text(0.537e-9, -4.8, r'-3.0',  color='r', size=17, rotation = 0)
    ax.text(1.27e-9, -4.8, r'-2.53', color='b', size=17, rotation = 0)
    ax.text(0.277e-8, -4.8, r'-2.53', color='r', size=17, rotation = 0)
    ax.text(7.2e-9, -4.8, r'-2.0',  color='b', size=17, rotation = 0)
    ax.text(1.6e-8,  -3., r'-2.0', color='r', size=17, rotation = 0)

#ax.text(1.23e-10, -4.8, r'$\Gamma$ = -3.0', color='b', size=18, rotation = 0)
#ax.text(1.2e-9, -4.8, r'-2.53', color='b', size=17, rotation = 0)
#ax.text(7.3e-9, -4.8, r'-2.0',  color='b', size=17, rotation = 0)

ax.text(1.3e-10, -5.3, r'$\Gamma$ = -3.0', color='b', size=18, rotation = 0)
ax.text(1.25e-9, -5.3, r'-2.53', color='b', size=17, rotation = 0)
ax.text(7.6e-9, -5.3, r'-2.0',  color='b', size=17, rotation = 0)

ax.text(3.6e-10, -2.5, r'-3.0',  color='r', size=17, rotation = 0)
#ax.text(7.3e-10, -2.5, r'-3.0',  color='r', size=17, rotation = 0)
ax.text(0.189e-8, -2.5, r'-2.53', color='r', size=17, rotation = 0)
#ax.text(5.75e-9,  -2.5, r'-2.0', color='r', size=17, rotation = 0)
ax.text(1.14e-8,  -2.5, r'-2.0', color='r', size=17, rotation = 0)


#ax.annotate('', xytext=(8e-10, -3.84), xy=(8e-10, -3),
#        arrowprops=dict(headlength=0.4,headwidth=0.2),)

ax.set_xlabel(r"$E_\nu^2dF/dE_\nu$ at 100 TeV  [ GeVcm$^{-2}$s$^{-1}$sr$^{-1}$ ]"
        ,fontsize=20, labelpad=-3) #label pad to fix some thing flexibly
ax.set_ylabel(r"TS",fontsize=20)
#ax.arrow(1e-9,-4, 1e-10, 1)
#ax.set_ylabel(r"TS",fontsize=20, labelpad=-3)
ax.set_xlim(5e-11,1e-7)
#use.autoscale_y(ax)
ax.set_ylim(-10,1)
ax.legend(loc='best',prop={'size':16})  # Larger if used for a paper.

#ax.set_yticks([1, 0, -1, -2,-3,-4,-5,-6,-7,-8,-9,-10])
#ax.set_yticklabels(['1', '0', '-1', '-2','-3','-4','-5','-6','-7','-8','-9','-10'])

ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)

ax.yaxis.get_ticklocs(minor=True)
ax.minorticks_on()


#plt.savefig('figures/TS_flux.pdf',bbox_inches='tight', pad_inches=0.1)
plt.show()
'''








# Fluxes
'''
fig = plt.figure(figsize=(6, 6), facecolor='w')
ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
ax.set_xscale('log'); ax.set_yscale('log')

Enus = use.ebs(1e2,1e9, 7*100)

idx = 2

def dIdEnu0(Enus): # -2.53
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    'Use the measured results by IC coll, in 2001.09520'
    return 1.66e-18*(Enus/1e5)**(-2.53)*3 
def dIdEnu1(Enus): # -2.
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.)*3 
def dIdEnu3(Enus): # -2.28
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.28)*3 
def dIdEnu2(Enus): # -3.
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-3.)*3 


#tmp = loadtxt('./data_input/2001.09520_fig3_astro_flux_C.dat').T
#ax.plot(tmp[0], tmp[1],'b--',label=r'',lw=1.5,ms=2) 
tmp1 = loadtxt('./data_input/2001.09520_fig3_astro_flux_U.dat').T
ax.plot(tmp1[0], tmp1[1]*3,'g-',label=r'',lw=1.5,ms=2) 
tmp2 = loadtxt('./data_input/2001.09520_fig3_astro_flux_L.dat').T
ax.plot(tmp2[0], tmp2[1]*3,'g-',label=r'',lw=1.5,ms=2) 
xxs, yys = use.org_data( [tmp1[0],tmp2[0]],[tmp1[1]*3,tmp2[1]*3], fill_value_='extrapolate', nlogbins=1000  )
ax.fill_between(xxs, yys[0], yys[1],\
        facecolor='#6dd4b2')##edee63')

indx = where( (Enus>=tmp1[0][0])*(Enus<=tmp1[0][-1]) ) 
xx = Enus[indx]; yy = dIdEnu0(Enus[indx])*Enus[indx]**idx;
ax.plot(xx, yy, 'g-',label=r'',lw=1.5,ms=2) 

tmp_intp = intp.interp1d( log(xx), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
xx0 = use.ebs(16e3, 2.6e6, 10000)
#xx0 = use.ebs(16e3, 655000, 10000)
Eflux_int_IC = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print('# IceCube', Eflux_int_IC )


# Equal weighting
#def dIdEnuX(Enus): # -2.X # hardest spec allowed for the Eq weighting
#    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
#    'Copied from ns2flux.py'
#    return 5e-18/3.*(Enus/1e5)**(-2.15)*3 
#yy = 942.6764054813099/3807.2542914797045*dIdEnuX(Enus)*Enus**idx
#ax.plot(Enus, yy,'r--',label=r'',lw=1.5,ms=2)  # 1851.3768727781967 is from llh fit
#tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
#Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
#print( Eflux_int/Eflux_int_IC )


# -2.0
yy = 913.1448105049642/3281.23*dIdEnu1(Enus)*Enus**idx
ax.plot(Enus,  yy,'r--',label=r'',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print(Eflux_int/Eflux_int_IC )




# -2.53
yy = 914.9986/8845.71*dIdEnu0(Enus)*Enus**idx 
ax.plot(Enus, yy,'r-',label=r'Equal weighting',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print( Eflux_int/Eflux_int_IC )

#ax.plot(Enus, 1900.56/3281.23*dIdEnu1(Enus)*Enus**idx,'r--',label=r'Equal Weighting, $\Gamma=-2.0$',lw=1.5,ms=2) 
#ax.plot(Enus, 1827.86/4754.45*dIdEnu3(Enus)*Enus**idx,'r--',label=r'Equal Weighting, $\Gamma=-2.28$',lw=1.5,ms=2) 

# -3.0
yy = 855.60/49250.32*dIdEnu2(Enus)*Enus**idx
ax.plot(Enus, yy, 'r-.',label=r'',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print(Eflux_int/Eflux_int_IC )


# X-band flux weighting
# -2.0
yy = 412.142671524149361/3281.23*dIdEnu1(Enus)*Enus**idx
ax.plot(Enus,  yy,'b--',label=r'',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print(Eflux_int/Eflux_int_IC )

#ax.plot(Enus,  655.21/4754.45*dIdEnu3(Enus)*Enus**idx,'b--',label=r'8 GHz flux Weighting, $\Gamma=-2.28$',lw=1.5,ms=2) 


# - 2.53
yy = 426.68741891066287/8845.71*dIdEnu0(Enus)*Enus**idx
ax.plot(Enus,  426.68741891066287/8845.71*dIdEnu0(Enus)*Enus**idx,'b-',label=r'X-band flux density weighting',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print(Eflux_int/Eflux_int_IC )


# -3.0
yy = 413.21768249810657/49250.32*dIdEnu2(Enus)*Enus**idx
ax.plot(Enus, 413.21768249810657/49250.32*dIdEnu2(Enus)*Enus**idx,'b-.',label=r'',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print( Eflux_int/Eflux_int_IC )


Length=1.8
ax.annotate('', xytext=(2.85e4, 1.4715e-9), 
                    xy=(2.85e4, 1.4715e-9/Length),
        arrowprops=dict(color='b', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(5.e4, 1.737e-9), 
                    xy=(5.e4, 1.737e-9/Length),
        arrowprops=dict(color='r', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(2.366e5, 1.522e-9), 
                    xy=(2.366e5, 1.522e-9/Length),
        arrowprops=dict(color='b', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(4.02e5, 2.464e-9), 
                    xy=(4.02e5, 2.464e-9/Length),
        arrowprops=dict(color='r', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(2.9e5, 6.279e-9), 
                    xy=(2.9e5, 6.279e-9/Length),
        arrowprops=dict(color='b', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(4.6e5, 1.391e-8), 
                    xy=(4.6e5, 1.391e-8/Length),
        arrowprops=dict(color='r', width=0.8, headwidth=4, headlength=8, shrink=0.01),)

ax.text(1.6e4, 1.68e-8,r'Tot. astroph. $\nu$ flux (IceCube)', color='g', size=18, rotation = -25.7)

#ax.text(2.8e3, 2.3e-9,r'$\Gamma=$ -3.0', color='b', size=18, rotation = 0)
ax.text(2.4e4, 2.6e-10,r'$\Gamma=$ -3.0', color='b', size=18, rotation = 0)
ax.text(6.5e5, 5.99e-10,r'-2.53', color='b', size=18, rotation = -27)
ax.text(7.5e4, 6.8e-9,r'-2.0', color='b', size=18, rotation = 0)

ax.text(2.e5, 4.5e-10,r'-3.0', color='r', size=18, rotation = 0)
ax.text(1.5e6, 0.83e-9,r'-2.53', color='r', size=18, rotation = -27)
ax.text(1.3e5, 1.5e-8,r'-2.0', color='r', size=18, rotation = 0)

ax.set_xlabel(r"$E_\nu$  [ GeV ]",fontsize=20, labelpad=6) #label pad to fix some thing flexibly
ax.set_ylabel(r"$E_\nu^2dF/dE_\nu$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
ax.set_xlim(1e3,1e7)
use.autoscale_y(ax)
ax.set_ylim(4e-11,3e-7)
ax.legend(loc='lower left',prop={'size':16})  # Larger if used for a paper.
ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
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
#plt.grid()#ls='-', lw=0.5)
plt.savefig('figures/Fluxes.pdf',bbox_inches='tight', pad_inches=0.1)
plt.show()
'''


# TS values of the stacking analysis with injected signal events
'''
fig = plt.figure(figsize=(6, 6), facecolor='w')
ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
#ax.set_xscale('log'); ax.set_yscale('log')
ax.set_xscale('linear'); ax.set_yscale('linear')

tmp = loadtxt('./data_output_new_data_inj/results_Mthd2.dat').T
ax.plot( tmp[2]/8845.71, sqrt(tmp[1]),'ro-',label=r'',lw=1.5,ms=2) 

ax.set_xlabel(r"Fraction of total astrophysical $\nu$ flux injected",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
ax.set_ylabel(r"$\sqrt{\rm TS_{max}}$",fontsize=20)
ax.set_xlim(0, 1.05)
ax.set_ylim(0, 22.5)
#ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.

#ax.set_xticks(      [0,   0.2,   0.4,   0.6,   0.8 ,  1])
#ax.set_xticklabels(['0', '0.2', '0.4', '0.6', '0.8', '1'])

ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=22)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=22)
ax.yaxis.get_ticklocs(minor=True)
ax.minorticks_on()
plt.savefig('./Tex_20201030_HEnu_radio_quasars/TS_injectedSignals.pdf',bbox_inches='tight', pad_inches=0.1)
plt.show()
'''

#########################################################################

# TS v.s. Flux , 3yr data
'''
fig = plt.figure(figsize=(6, 6), facecolor='w')
ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
ax.set_xscale('log'); ax.set_yscale('linear')

def dIdEnu0(Enus): # -2.53
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    'Use the measured results by IC coll, in 2001.09520'
    return 1.66e-18*(Enus/1e5)**(-2.53)*3 
def dIdEnu1(Enus): # -2.
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.)*3 
def dIdEnu3(Enus): # -2.28
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.28)*3 
def dIdEnu2(Enus): # -3.
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-3.)*3 
def dIdEnuX(Enus): # -2.X # hardest spec allowed for the Eq weighting
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.15)*3 


idx = 2;
E0 = 1e5;

ax.plot( [ dIdEnu0(E0)*E0**2 , dIdEnu0(E0)*E0**2 ], [-100, 10],'g-',label=r'',lw=1.5,ms=2) # checked
ax.plot( [ 3.83e-8 , 3.83e-8 ], [-100, 10],'g-',label=r'',lw=1.5,ms=2) \
        # checked # LL
ax.plot( [ 6.165e-8 , 6.165e-8 ], [-100, 10],'g-',label=r'',lw=1.5,ms=2) \
        # checked # UL
ax.axvspan(3.83e-8, 6.165e-8, alpha=1, color='#6dd4b2')

#tmp = loadtxt('data_output_old_data/RQs3386_3yrNu_TSns_WeightEq_GM2.15.dat').T
#ax.plot(tmp[0]/1129.72*dIdEnuX(E0)*E0**idx, tmp[1],'r--',label=r'',lw=1.5,ms=2)
#print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 1129.72*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV

tmp = loadtxt('data_output_old_data/RQs3386_3yrNu_TSns_WeightEq_GM2.53.dat').T
ax.plot(tmp[0]/2666.05*dIdEnu0(E0)*E0**idx, tmp[1],'r-',label=r'Equal weighting',lw=1.5,ms=2) # 4.98 = 3*1.66
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 2666.05*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV

tmp = loadtxt('data_output_old_data/RQs3386_3yrNu_TSns_WeightEq_GM3.0.dat').T
ax.plot(tmp[0]/15238.29*dIdEnu2(E0)*E0**idx, tmp[1],'r-.',label=r'',lw=1.5,ms=2)
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 15238.29*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV


tmp = loadtxt('data_output_old_data/RQs3386_3yrNu_TSns_WeightXFlux_GM2.0.dat').T
ax.plot(tmp[0]/969.42*dIdEnu1(E0)*E0**idx, tmp[1],'b--',label=r'',lw=1.5,ms=2) 
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 969.42*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV

tmp = loadtxt('data_output_old_data/RQs3386_3yrNu_TSns_WeightXFlux_GM2.53.dat').T
ax.plot(tmp[0]/2666.05*dIdEnu0(E0)*E0**idx, tmp[1],'b-',label=r'X-band flux-density weighting',lw=1.5,ms=2) 
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 2666.05*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV

tmp = loadtxt('data_output_old_data/RQs3386_3yrNu_TSns_WeightXFlux_GM3.0.dat').T
ax.plot(tmp[0]/15238.29*dIdEnu2(E0)*E0**idx, tmp[1],'b-.',label=r'',lw=1.5,ms=2) 
print( intp.interp1d( tmp[1], tmp[0], kind='linear')(-3.84) / 15238.29*dIdEnu0(E0)*E0**idx / (dIdEnu0(E0)*E0**2)  ) # Fraction at 100 TeV


ax.text(2.9e-10,  1.35, r'Tot. astroph. $\nu$ flux at 100 TeV', color='g', size=18, rotation = 0)
ax.text(7.25e-9,  0.8, r'(IceCube)', color='g', size=18, rotation = 0)
ax.plot( [1e-12, 1e-7], [-3.84, -3.84],'k--',label=r'',lw=1.7,ms=2)
ax.text( 0.6e-10, -3.73, r'$95\%$ limit', color='k', size=18, rotation = 0)
ax.annotate('', xytext=(3.07e-10, -3.84), 
                    xy=(3.07e-10, -3),
        arrowprops=dict(color='k', width=0.8, headwidth=4, headlength=8, shrink=0.01),)

for i in range(0):
    ax.text(1.38e-10, -4.8, r'$\Gamma$ = -3.0', color='b', size=18, rotation = 0)
    ax.text(0.537e-9, -4.8, r'-3.0',  color='r', size=17, rotation = 0)
    ax.text(1.27e-9, -4.8, r'-2.53', color='b', size=17, rotation = 0)
    ax.text(0.277e-8, -4.8, r'-2.53', color='r', size=17, rotation = 0)
    ax.text(7.2e-9, -4.8, r'-2.0',  color='b', size=17, rotation = 0)
    ax.text(1.6e-8,  -3., r'-2.0', color='r', size=17, rotation = 0)

#ax.text(1.23e-10, -4.8, r'$\Gamma$ = -3.0', color='b', size=18, rotation = 0)
#ax.text(1.2e-9, -4.8, r'-2.53', color='b', size=17, rotation = 0)
#ax.text(7.3e-9, -4.8, r'-2.0',  color='b', size=17, rotation = 0)

ax.text(2.5e-10, -5.3, r'$\Gamma$ = -3.0', color='b', size=18, rotation = 0)
ax.text(2.49e-9, -5.3, r'-2.53', color='b', size=17, rotation = 0)
#ax.text(8.3e-9, -5.3, r'-2.0',  color='b', size=17, rotation = 0)
ax.text(1.65e-8, -5.3, r'-2.0',  color='b', size=17, rotation = 0)

ax.text(8.2e-10, -2.5, r'-3.0',  color='r', size=17, rotation = 0)
#ax.text(7.3e-10, -2.5, r'-3.0',  color='r', size=17, rotation = 0)
ax.text(0.43e-8, -2.5, r'-2.53', color='r', size=17, rotation = 0)
#ax.text(5.75e-9,  -2.5, r'-2.0', color='r', size=17, rotation = 0)
#ax.text(1.25e-8,  -2.5, r'-2.0', color='r', size=17, rotation = 0)


#ax.annotate('', xytext=(8e-10, -3.84), xy=(8e-10, -3),
#        arrowprops=dict(headlength=0.4,headwidth=0.2),)

ax.set_xlabel(r"$E_\nu^2dF/dE_\nu$ at 100 TeV  [ GeVcm$^{-2}$s$^{-1}$sr$^{-1}$ ]"
        ,fontsize=20, labelpad=None) #label pad to fix some thing flexibly
ax.set_ylabel(r"TS",fontsize=20)
#ax.arrow(1e-9,-4, 1e-10, 1)
#ax.set_ylabel(r"TS",fontsize=20, labelpad=-3)
ax.set_xlim(5e-11,1e-7)
#use.autoscale_y(ax)
ax.set_ylim(-10,2)
ax.legend(loc='best',prop={'size':16})  # Larger if used for a paper.

#ax.set_yticks([1, 0, -1, -2,-3,-4,-5,-6,-7,-8,-9,-10])
#ax.set_yticklabels(['1', '0', '-1', '-2','-3','-4','-5','-6','-7','-8','-9','-10'])

ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)

ax.yaxis.get_ticklocs(minor=True)
ax.minorticks_on()


plt.savefig('./Tex_20201030_HEnu_radio_quasars/TS_flux_3yr.pdf',bbox_inches='tight', pad_inches=0.1)
plt.show()
'''



# Fluxes 3 yr
'''
fig = plt.figure(figsize=(6, 6), facecolor='w')
ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
ax.set_xscale('log'); ax.set_yscale('log')

Enus = use.ebs(1e2,1e9, 7*100)

idx = 2

def dIdEnu0(Enus): # -2.53
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    'Use the measured results by IC coll, in 2001.09520'
    return 1.66e-18*(Enus/1e5)**(-2.53)*3 
def dIdEnu1(Enus): # -2.
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.)*3 
def dIdEnu3(Enus): # -2.28
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.28)*3 
def dIdEnu2(Enus): # -3.
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-3.)*3 


#tmp = loadtxt('./data_input/2001.09520_fig3_astro_flux_C.dat').T
#ax.plot(tmp[0], tmp[1],'b--',label=r'',lw=1.5,ms=2) 
tmp1 = loadtxt('./data_input/2001.09520_fig3_astro_flux_U.dat').T
ax.plot(tmp1[0], tmp1[1]*3,'g-',label=r'',lw=1.5,ms=2) 
tmp2 = loadtxt('./data_input/2001.09520_fig3_astro_flux_L.dat').T
ax.plot(tmp2[0], tmp2[1]*3,'g-',label=r'',lw=1.5,ms=2) 
xxs, yys = use.org_data( [tmp1[0],tmp2[0]],[tmp1[1]*3,tmp2[1]*3], fill_value_='extrapolate', nlogbins=1000  )
ax.fill_between(xxs, yys[0], yys[1],\
        facecolor='#6dd4b2')##edee63')

indx = where( (Enus>=tmp1[0][0])*(Enus<=tmp1[0][-1]) ) 
xx = Enus[indx]; yy = dIdEnu0(Enus[indx])*Enus[indx]**idx;
ax.plot(xx, yy, 'g-',label=r'',lw=1.5,ms=2) 

tmp_intp = intp.interp1d( log(xx), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
xx0 = use.ebs(16e3, 2.6e6, 10000)
#xx0 = use.ebs(16e3, 655000, 10000)
Eflux_int_IC = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print('# IceCube', Eflux_int_IC )


# Equal weighting
#def dIdEnuX(Enus): # -2.X # hardest spec allowed for the Eq weighting
#    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
#    'Copied from ns2flux.py'
#    return 5e-18/3.*(Enus/1e5)**(-2.15)*3 
#yy = 942.6764054813099/3807.2542914797045*dIdEnuX(Enus)*Enus**idx
#ax.plot(Enus, yy,'r--',label=r'',lw=1.5,ms=2)  # 1851.3768727781967 is from llh fit
#tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
#Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
#print( Eflux_int/Eflux_int_IC )

def dIdEnuX(Enus): # -2.X # hardest spec allowed for the Eq weighting
    'Flux of all nus; Output: GeV-1cm-2s-1sr-1'
    'Copied from ns2flux.py'
    return 5e-18/3.*(Enus/1e5)**(-2.15)*3


# -2.15
yy =  596.0256926343257/1129.72*dIdEnuX(Enus)*Enus**idx
ax.plot(Enus,  yy,'r--',label=r'',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print(Eflux_int/Eflux_int_IC )


# -2.53
yy = 573.4268845812157/2666.05*dIdEnu0(Enus)*Enus**idx 
ax.plot(Enus, yy,'r-',label=r'Equal weighting',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print( Eflux_int/Eflux_int_IC )

#ax.plot(Enus, 1900.56/3281.23*dIdEnu1(Enus)*Enus**idx,'r--',label=r'Equal Weighting, $\Gamma=-2.0$',lw=1.5,ms=2) 
#ax.plot(Enus, 1827.86/4754.45*dIdEnu3(Enus)*Enus**idx,'r--',label=r'Equal Weighting, $\Gamma=-2.28$',lw=1.5,ms=2) 

# -3.0
yy = 550.6680884436383/15238.29*dIdEnu2(Enus)*Enus**idx
ax.plot(Enus, yy, 'r-.',label=r'',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print(Eflux_int/Eflux_int_IC )


# X-band flux weighting
# -2.0
yy = 257.8587307194603/969.42*dIdEnu1(Enus)*Enus**idx
ax.plot(Enus,  yy,'b--',label=r'',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print(Eflux_int/Eflux_int_IC )

#ax.plot(Enus,  655.21/4754.45*dIdEnu3(Enus)*Enus**idx,'b--',label=r'8 GHz flux Weighting, $\Gamma=-2.28$',lw=1.5,ms=2) 


# - 2.53
yy =  259.38250668909086/2666.05*dIdEnu0(Enus)*Enus**idx
ax.plot(Enus,  259.38250668909086/2666.05*dIdEnu0(Enus)*Enus**idx,'b-',label=r'X-band flux density weighting',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print(Eflux_int/Eflux_int_IC )


# -3.0
yy = 244.83631234974698/15238.29*dIdEnu2(Enus)*Enus**idx
ax.plot(Enus, 244.83631234974698/15238.29*dIdEnu2(Enus)*Enus**idx,'b-.',label=r'',lw=1.5,ms=2) 
tmp_intp = intp.interp1d( log(Enus), log(yy), kind='linear', bounds_error=False, fill_value='extrapolate');
Eflux_int = integrate.simps( exp( tmp_intp( log(xx0) ) ), log(xx0) ) # no need multiply xx0 in the integrand cuz yy already did.
print( Eflux_int/Eflux_int_IC )


Length=1.8
ax.annotate('', xytext=(2.85e4, 1.4715e-9), 
                    xy=(2.85e4, 1.4715e-9/Length),
        arrowprops=dict(color='b', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(5.e4, 1.737e-9), 
                    xy=(5.e4, 1.737e-9/Length),
        arrowprops=dict(color='r', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(2.366e5, 1.522e-9), 
                    xy=(2.366e5, 1.522e-9/Length),
        arrowprops=dict(color='b', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(4.02e5, 2.464e-9), 
                    xy=(4.02e5, 2.464e-9/Length),
        arrowprops=dict(color='r', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(2.9e5, 6.279e-9), 
                    xy=(2.9e5, 6.279e-9/Length),
        arrowprops=dict(color='b', width=0.8, headwidth=4, headlength=8, shrink=0.01),)
ax.annotate('', xytext=(4.6e5, 1.391e-8), 
                    xy=(4.6e5, 1.391e-8/Length),
        arrowprops=dict(color='r', width=0.8, headwidth=4, headlength=8, shrink=0.01),)

ax.text(1.6e4, 1.68e-8,r'Tot. astroph. $\nu$ flux (IceCube)', color='g', size=18, rotation = -25.7)

#ax.text(2.8e3, 2.3e-9,r'$\Gamma=$ -3.0', color='b', size=18, rotation = 0)
ax.text(2.4e4, 2.6e-10,r'$\Gamma=$ -3.0', color='b', size=18, rotation = 0)
ax.text(6.5e5, 5.99e-10,r'-2.53', color='b', size=18, rotation = -27)
ax.text(7.5e4, 6.8e-9,r'-2.0', color='b', size=18, rotation = 0)

ax.text(2.e5, 4.5e-10,r'-3.0', color='r', size=18, rotation = 0)
ax.text(1.5e6, 0.83e-9,r'-2.53', color='r', size=18, rotation = -27)
ax.text(1.3e5, 1.5e-8,r'-2.0', color='r', size=18, rotation = 0)

ax.set_xlabel(r"$E_\nu$  [ GeV ]",fontsize=20, labelpad=6) #label pad to fix some thing flexibly
ax.set_ylabel(r"$E_\nu^2dF/dE_\nu$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
ax.set_xlim(1e3,1e7)
use.autoscale_y(ax)
ax.set_ylim(4e-11,3e-7)
ax.legend(loc='lower left',prop={'size':16})  # Larger if used for a paper.
ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
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
#plt.grid()#ls='-', lw=0.5)
plt.savefig('./Tex_20201030_HEnu_radio_quasars/Fluxes_3yr.pdf',bbox_inches='tight', pad_inches=0.1)
plt.show()
'''

# bkup
