#!/usr/bin/python
# -*- coding:utf-8 -*- 
import astropy.io.fits as pf
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
import os,datetime
import use
#set_printoptions(suppress=True)
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

#####################################  ######################################
#################################### !! #####################################

d2r = 180./pi

################################ Atm nu flux #################################
tmp1 = loadtxt('./data_input/HKKM2015_atm_nu_flux_SouthPole_solarMin.dat').T
Enu1 = tmp1[0];
Fnu1 = (tmp1[1]+tmp1[2])*1e-4  # m-2s-1GeV-1sr-1 -> cm-2s-1GeV-1sr-1
Fnu1_intp = intp.interp1d( log(Enu1), log(Fnu1), kind='linear', bounds_error=False, fill_value=-inf)

tmp2 = loadtxt('../20180725_Tridents_HE/data_input/IceCube_6yr_atm.dat').T
Enu2 = tmp2[0];
Fnu2 = tmp2[1]/1.13/Enu2/Enu2 #!
Fnu2_intp = intp.interp1d( log(Enu2), log(Fnu2), kind='linear', bounds_error=False, fill_value=-inf)

def dIdEnu_atm(Enus):
    'Flux of numu+numubar; Output: GeV-1cm-2s-1sr-1'
    tmp4 = zeros(Enus.shape)
    idx1 = where(Enus<=1e4)
    tmp4[idx1] = exp(Fnu1_intp(log(Enus[idx1])))
    idx2 = where(Enus>1e4)
    tmp4[idx2] = exp(Fnu2_intp(log(Enus[idx2])))
    return tmp4

## zenith depdendent flux.
#tmp3 = loadtxt('data_input/spl-ally-20-01-solmin.dat')
#tmp5 = (tmp3[:,1]+tmp3[:,1])/2.*1e-4 # m-2 -> cm-2
#tmp5 = tmp5.reshape(20,-1).T # cols are different zenith; rows are different Es
############################### !Atm nu flux! ################################

# Astro nu flux
def dIdEnu(Enus):
    'Flux of numu+numubar; Output: GeV-1cm-2s-1sr-1; This way is better to compare with Hooper results'
    'Use the measured results by IC coll, in 1507.03991, as used by Hooper'
    N0 = 1.2e-7/3.; \
        # For the measured astro nu flux in Hooper ppr, which is from 1507.03991
    return N0*(Enus/3e4)**(-0.5)/Enus/Enus

def dIdEnu(Enus): # -2.28
    'Flux of numu+numubar; Output: GeV-1cm-2s-1sr-1'
    return 5e-18/3.*(Enus/1e5)**(-2.28) #!

def dIdEnu(Enus): # -2.53
    'Flux of numu+numubar; Output: GeV-1cm-2s-1sr-1'
    'Use the measured results by IC coll, in 2001.09520'
    return 1.66e-18*(Enus/1e5)**(-2.53) #!

def dIdEnu(Enus): # -2.
    'Flux of numu+numubar; Output: GeV-1cm-2s-1sr-1'
    return 5e-18/3.*(Enus/1e5)**(-2.) #!

def dIdEnu(Enus): # -3.
    'Flux of numu+numubar; Output: GeV-1cm-2s-1sr-1'
    return 5e-18/3.*(Enus/1e5)**(-3.) #!

def dIdEnu(Enus): # -2.X # test
    'Flux of numu+numubar; Output: GeV-1cm-2s-1sr-1'
    return 5e-18/3.*(Enus/1e5)**(-2.15) #!


EAfilenms = array([ 
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC40_effectiveArea.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC59_effectiveArea.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC79_effectiveArea.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC86_I_effectiveArea.csv', # cdx
    './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/irfs/IC86_II_effectiveArea.csv', # cdx
    ])
Ntots = array([ 36843., 106980.,  93107., 135874., 760639.]) #!
#Ntots = array([ 14121.,  42754.,  48361.,  61313., 500072. ]) # For northern sky


# uptime
for j in range(1):
    uptime_flms = array([
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC40_exp.csv', # cdx
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC59_exp.csv', # cdx
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC79_exp.csv', # cdx
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC86_I_exp.csv', # cdx
        './data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/uptime/IC86_II2VII_exp_BZ.csv', # cdx
        ]) #!
    
    uptimes = zeros( len(uptime_flms) );
    for i in range(len(uptime_flms)):
        tmp = loadtxt(uptime_flms[i])
        uptimes[i] = sum(tmp[:,1]-tmp[:,0])


#i = 4

n_s_astros = zeros( len(Ntots) )
for i in range( len(Ntots) ):
    tmp = loadtxt(EAfilenms[i]); Ntot = float(Ntots[i]); uptime = uptimes[i]
    
    Es = 10**( unique(tmp[:,0] )/2.+unique( tmp[:,1])/2. )
    coszeniths = ( cos(90./d2r + unique(tmp[:,2])/d2r) + cos(90./d2r + unique(tmp[:,3])/d2r) )/2.
    Aeff = tmp[:,4]
    Aeff = Aeff.reshape( len(coszeniths),-1 )
    Aeff = sum(Aeff, axis=0)/50. #50 is to normalize  #!
    #Aeff = sum(Aeff[25:50,:], axis=0)/25./2. # For northern sky \
            # /2. is for northern sky flux. Above tens GeV, north and south fluxes have the same zenith dep.
    idx = where( Aeff>0 ); Aeff=Aeff[idx]; Es=Es[idx];
    Aeff_intp =  intp.interp1d( log(Es), log(Aeff), kind='linear', bounds_error=False, fill_value='extrapolate') 
            # only increase by ~0.02 compared to above for IC86b.  Later might look into this ###!!!!!!!!!!!!!!!!!!!!!!!
    
    Enus = use.ebs(1e1,1e10,9*1000); Aeff = exp( Aeff_intp(log(Enus)) )
    
    # Calc
    # for atm nu, to cmpr w/ dat and get scaling factor
    dNdEnu =  Aeff* dIdEnu_atm(Enus) * uptime*24*3600 *4*pi; 
    EdNdEnu = dNdEnu*Enus; Emus = Enus*0.75 # checked # didn't affect rslt much.
    idx = where(Emus>0.) # no different from using 0. #!
    ns_atm = integrate.simps(EdNdEnu[idx], log(Emus[idx]))
    print('n_s for atm nu:', ns_atm )
    fac = Ntot/ns_atm
    print('factor:', fac ) 
    
    dNdEnu =  Aeff* dIdEnu(Enus) * uptime*24*3600 *4*pi #
    EdNdEnu = dNdEnu*Enus; Emus = Enus*0.75 # checked # didn't affect rslt much.
    idx = where(Emus>0.) # no different from using 0. #!
    n_s_astros[i] = integrate.simps(EdNdEnu[idx], log(Emus[idx]))*fac 
    print('n_s for astroph nu:', n_s_astros[i] )
    print()
    #print( dIdEnu(30.e3)*30.e3**2.*1.e-3*3 ) # EFlux@30TeV, 1e-3 is4 GeVcm-2s-1sr-1 -> TeV cm-2s-1sr-1, *3 is4 numunumubar -> all 6 flavor

#print('n_s astro for 2010--2012 is:', n_s_astros[2]+n_s_astros[3]+n_s_astros[4]/6)
#print('n_s astro tot is :', n_s_astros.sum())

exit()

for i in range(0): # plot atm nu
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('log'); ax.set_yscale('log')
    
    tmp = loadtxt('./data_input/HKKM2015_atm_nu_flux_SouthPole_solarMin.dat').T
    Enu = tmp[0];
    Fnu = (tmp[1]+tmp[2])*1e-4  # m-2s-1GeV-1sr-1 -> cm-2
    ax.plot(Enu, Enu**2*Fnu,'ro-',label=r'',lw=1.5,ms=2) 
    
    tmp = loadtxt('../20180725_Tridents_HE/data_input/IceCube_6yr_atm.dat').T
    ax.plot(tmp[0], tmp[1]/1.13,'bo-',label=r'',lw=1.5,ms=2) 

    Enus = use.ebs(1e1,1e6,1000)
    ax.plot(Enus, dIdEnu_atm(Enus)*Enus**2,'k-',label=r'',lw=1.5,ms=2) 

    
    ax.set_xlabel(r"$E$  [ GeV ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    ax.set_ylabel(r"$E^2dN/dE$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
    ax.set_xlim()
    use.autoscale_y(ax)
    ax.set_ylim()
    ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    plt.grid()#ls='-', lw=0.5)
    plt.show()
    exit()

for i in range(0): # plot EA
    fig = plt.figure(figsize=(6, 6), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('log'); ax.set_yscale('log')
    
    ax.plot(Es, Aeff,'ro-',label=r'',lw=1.5,ms=2) 
    
    ax.set_xlabel(r"$E_\nu$  [ GeV ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    ax.set_ylabel(r"[ cm$^{2}$ ]",fontsize=20)
    ax.set_xlim()
    use.autoscale_y(ax)
    ax.set_ylim()
    ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
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
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    plt.grid()#ls='-', lw=0.5)
    plt.show()
    exit()




#backup

# EA, for old data
#tmp = loadtxt('data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/TabulatedAeff.txt'); Ntot = 138322.

#tmp = loadtxt('data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC79-2010-TabulatedAeff.txt'); Ntot = 93107.
#tmp = loadtxt('data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC86-2011-TabulatedAeff.txt'); Ntot = 135874.
#tmp = loadtxt('data_input/IceCube_data_released/All-sky_point-source_IceCube_data__years_2010-2012/IC86-2012-TabulatedAeff.txt'); Ntot = 105241.
#Es1 =tmp[:,0]; Es2 =tmp[:,1]; Aeff = tmp[:,4]
#Es = sqrt( Es1[0::200]*Es2[0::200] ) 
#Aeff = Aeff.reshape(-1,200) # Each row has same energy
#Aeff = sum(Aeff, axis=1)/200.*1e4 #200 is to normalize, m^2->cm^2 \
#        #Aeff = sum(Aeff[:,50:100], axis=1)/50. # reproduced black solid line of Figure.2 of 1406.6757. (Checked twice)
#        #Aeff = sum(Aeff[:,100:150], axis=1)/50. # reproduced red solid line of Figure.2 of 1406.6757. 
#Aeff_intp =  intp.interp1d( log(Es), log(Aeff), kind='linear', bounds_error=False, fill_value='extrapolate') 
