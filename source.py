#!/usr/bin/python
import astropy.io.fits as pf
from numpy import *
#from scipy import integrate
from scipy import interpolate as intp # Not used in this file yet but has to call it here becuase there is a numpy.intp()
from use1 import *
#import matplotlib.pyplot as plt 
#import os,datetime
#import use
#set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=6, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

'''
Need: N_src; RAs_src in rad; Decs_src in rad;
'''

#####################################  ######################################
#################################### !! #####################################
d2r = 180./pi




for ii in range(0): # SMBH from Ranjan # 20250200
    #tmp = loadtxt('../../1work_ptnl/20250221_SMBH_Ranjan/data_input/20250221_SMBBHS_data_catalog.txt', dtype=str) #, delimiter='&')
    tmp = loadtxt('../../1work_ptnl/20250221_SMBH_Ranjan/data_input/20250318_All_SMBBHs_data.txt', dtype=str)
    RAs_src  = array(tmp.T[1], dtype=float)/d2r  # 0 -- 360
    Decs_src = array(tmp.T[2], dtype=float)/d2r  # -90 to 90
    N_src = len(RAs_src)
    print('# N_src', N_src)

    DLs_src = array(tmp.T[4], dtype=float)  # -90 to 90
    indx = where( DLs_src>0 )
    RAs_src = RAs_src[indx]
    Decs_src = Decs_src[indx]
    N_src = len(RAs_src)
    print('# N_src', N_src)
    DLs_src = DLs_src[indx]
    W_mdls_src = 1/DLs_src**2
    #print( where( DLs_src==0 ) )
    #print( RAs_src*d2r ) 
    #print( Decs_src*d2r )

for ii in range(0): # SMBH from Ranjan # 20250400
    from astropy.cosmology import Planck18 as cosmo
    def DL(z):
        return cosmo.luminosity_distance(z).cgs.value
    #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_input/20250221_SMBBHS_data_catalog.txt', dtype=str) #, delimiter='&')
    #tmp = loadtxt('../20250221_SMBHB_Ranjan/data_input/20250404_pdf_datas_corrected/All_SMBBHs_updated_data.txt', dtype=str)
    tmp = loadtxt('../20250221_SMBHB_Ranjan/data_input/20250404_pdf_datas_corrected/All_SMBBHs_with_Neutrino_Weight.txt', dtype=str)
    RAs_src  = array(tmp.T[1], dtype=float)/d2r  # 0 -- 360
    Decs_src = array(tmp.T[2], dtype=float)/d2r  # -90 to 90
    Is_Strong_arr = array(tmp.T[3], dtype=float)
    Is_QSO_1s = array(tmp.T[4], dtype=float)
    zs_src = array(tmp.T[5], dtype=float)
    Lbols_src = array(tmp.T[6], dtype=float)
    nu_flux_weight = array(tmp.T[9], dtype=float)
    N_src = len(RAs_src)
    print('# N_src', N_src)

    #idx = where( zs_src>0 )
    idx = where( (zs_src>0)*(Is_QSO_1s==1) )
    #idx = where( (zs_src>0)*(Is_Strong_arr==1) )
    #idx = where( Is_QSO_1s==1 )
    #idx = where( Is_Strong_arr==1 )
    RAs_src = RAs_src[idx]
    Decs_src = Decs_src[idx]
    zs_src = zs_src[idx]
    DLs_src = DL(zs_src)
    Lbols_src = Lbols_src[idx]
    nu_flux_weight = nu_flux_weight[idx]
    N_src = len(RAs_src)
    print('# N_src', N_src)

    #W_mdls_src = 1/DLs_src**2
    #W_mdls_src = Lbols_src/DLs_src**2
    W_mdls_src = nu_flux_weight
    #print( where( nu_flux_weight>0 ) )
    #print( nu_flux_weight )


for ii in range(0): # first LHAASO catalog
    tmp = loadtxt('/Users/beizhou/Dropbox/1acdm/1work_ptnl/20231024_LHAASO_catalog_HEnu/data_input/2305.17030_table1_LHAASO_1st_catalog.dat', dtype=str, delimiter='&')
    print(tmp[66])
    RAs_src  = array(tmp.T[2], dtype=float)/d2r  # 0 -- 360
    Decs_src = array(tmp.T[3], dtype=float)/d2r  # -90 to 90
    N_src = len(RAs_src)
    print('# N_src', N_src)
    #print( RAs_src*d2r ) 
    #print( Decs_src*d2r )

############################# Single sources ################################
#N_src = 2
#RAs_src = array([40.67/d2r]*2); Decs_src = array([-0.01/d2r]*2) # NGC 1068
#RAs_src = array([ 77.35/d2r ]); Decs_src = array([ 5.70/d2r ])  # TXS0506
##RAs_src = array([ 77.3582/d2r ]); Decs_src = array([ 5.69314/d2r ])  # TXS0506
#RAs_src = array([ 235.75/d2r ]); Decs_src = array([ 61.50/d2r ]) # GB6 J1542+6129
#RAs_src = array([ 216.76/d2r ]); Decs_src = array([ 23.80/d2r ]) # GB6 J1542+6129
############################ !Single sources! ###############################


############################### Simulations #################################
for i in range(0):
    Nsrc = 5000  #!
    RAs_src = random.rand(Nsrc)*360/d2r 
    Decs_src = arcsin( random.rand(Nsrc)*2-1. ) # to get _srcs evenly distributed.
    
    idx = where( (Decs_src>-87./d2r)*(Decs_src<87./d2r) );
    RAs_src = RAs_src[idx] #[0:10000000]
    Decs_src = Decs_src[idx] #[0:10000000]
    N_src = len( RAs_src )
    
    print('# Number of _srcs:', N_src )
    #print(RAs_src*d2r)
    #print(RAs_src.max()*d2r)
    #print(RAs_src.min()*d2r)
    #print(Decs_src*d2r)
    #print(Decs_src.min()*d2r)
    #print(Decs_src.max()*d2r)
    savetxt('ttt.txt', array([ RAs_src*d2r, Decs_src*d2r ]).T)
############################## !Simulations! ################################


################################ Radio quasars #################################
for i in range(1): # for the HEnuRQ paper # cdx
    tmp = loadtxt('data_input/VLBI_rfc_2019c_cat_BZ.dat',dtype=str); print('# _srcs, 2019c')
    #tmp = loadtxt('data_input/VLBI_rfc_2020d_cat.dat',dtype=str); print('# _srcs, 2020c')
    # RA in 3 4 5; Dec in 6 7 8.;  X-band flux 17
    tmp1 = array(tmp[:,17], dtype=float)
    srcs = tmp[where( tmp1 >= 0.15)[0],:] \
            #3388 _srcs for 2019c; 
    
    deg     = array(srcs[:,6], dtype=float);\
            idx_deg_neg = where( char.ljust(srcs[:,6], 1) == '-' )
    minute  = array(srcs[:,7], dtype=float); minute[idx_deg_neg] *= -1
    sec     = array(srcs[:,8], dtype=float); sec[idx_deg_neg] *= -1
    Decs_src = (deg + minute/60. + sec/3600.)/d2r # checked the formula
    print('# Number of srcs before ...:', len(Decs_src) )
    
    srcs = srcs[ where((Decs_src<87./d2r)*(Decs_src>-87./d2r))[0],:] ###!!!
    #table_I_IVS_names = array(['1303-170', '2245+029', '0228-163', '1424+240', '0958+559']) # cdx
    #idx_table_I = array([ where(srcs[:,1] == nm)[0][0] for nm in table_I_IVS_names ]) # cdx
    #srcs = srcs[idx_table_I] # cdx
    N_src = len(srcs) 
    print('# Number of srcs:', N_src )
    
    # Get the RAs and Decs in degree
    hr     = array(srcs[:,3], dtype=float)
    minute = array(srcs[:,4], dtype=float)
    sec    = array(srcs[:,5], dtype=float)
    RAs_src = (hr + minute/60. + sec/3600.)/24.*360./d2r # checked the formula
    deg     = array(srcs[:,6], dtype=float);\
            idx_deg_neg = where( char.ljust(srcs[:,6], 1) == '-' )
    minute  = array(srcs[:,7], dtype=float); minute[idx_deg_neg] *= -1
    sec     = array(srcs[:,8], dtype=float); sec[idx_deg_neg] *= -1
    Decs_src = (deg + minute/60. + sec/3600.)/d2r # checked the formula
    
    W_mdls_src = array( srcs[:,17], dtype=float ) 
    src_IVS_names = srcs[:,1] # cdx
    src_J2000_names = srcs[:,2] # cdx
    print( RAs_src.shape )
    #print( RAs_src )
    
    #exit()

for i in range(0): # other purposes
    #tmp = loadtxt('data_input/VLBI_rfc_2019c_cat_BZ.dat',dtype=str); print('# _srcs, 2019c') #!
    tmp = loadtxt('data_input/VLBI_rfc_2020d_cat.dat',dtype=str); print('# srcs, 2020d')
    # RA in 3 4 5; Dec in 6 7 8.;  X-band flux 17

    tmp1 = array(tmp[:,17], dtype=float)
    #srcs = tmp[where( tmp1 >= 0.15)[0],:] \ #!
    srcs = tmp
    
    deg     = array(srcs[:,6], dtype=float);\
            idx_deg_neg = where( char.ljust(srcs[:,6], 1) == '-' )
    minute  = array(srcs[:,7], dtype=float); minute[idx_deg_neg] *= -1
    sec     = array(srcs[:,8], dtype=float); sec[idx_deg_neg] *= -1
    Decs_src = (deg + minute/60. + sec/3600.)/d2r # checked the formula
    print('# Number of srcs before ...:', len(Decs_src) )
    
    srcs = srcs[ where((Decs_src<87./d2r)*(Decs_src>-87./d2r))[0],:] # Now 3386 srcs
    N_src = len(srcs) 
    print('# Number of srcs:', N_src )
    
    # Get the RAs and Decs in degree
    hr     = array(srcs[:,3], dtype=float)
    minute = array(srcs[:,4], dtype=float)
    sec    = array(srcs[:,5], dtype=float)
    RAs_src = (hr + minute/60. + sec/3600.)/24.*360./d2r # checked the formula
    deg     = array(srcs[:,6], dtype=float);\
            idx_deg_neg = where( char.ljust(srcs[:,6], 1) == '-' )
    minute  = array(srcs[:,7], dtype=float); minute[idx_deg_neg] *= -1
    sec     = array(srcs[:,8], dtype=float); sec[idx_deg_neg] *= -1
    Decs_src = (deg + minute/60. + sec/3600.)/d2r # checked the formula
    
    W_mdls_src = array( srcs[:,17], dtype=float ) 
    
    #exit()
############################### !Radio quasars! ################################


############################ Radio quasars 15 GHz #############################
'''
for i in range(0):
    # result, 0.54 sigma for eq weighting; <0 sigma for U-band weighting...
    tmp = loadtxt('data_input/VLBI_rfc_2020d_cat.dat',dtype=str); print('# srcs, 2019c')
    #tmp = loadtxt('data_input/VLBI_rfc_2020c_cat_BZ.dat',dtype=str); print('# srcs, 2020c')
    # RA in 3 4 5; Dec in 6 7 8.;  X-band flux 17; U band flux 19;
    tmp1 = array(tmp[:,19], dtype=float)
    srcs = tmp[where( tmp1 >= 1.5)[0],:] \
            #3388 srcs for 2019c; 
    
    deg     = array(srcs[:,6], dtype=float);\
            idx_deg_neg = where( char.ljust(srcs[:,6], 1) == '-' )
    minute  = array(srcs[:,7], dtype=float); minute[idx_deg_neg] *= -1
    sec     = array(srcs[:,8], dtype=float); sec[idx_deg_neg] *= -1
    Decs_src = (deg + minute/60. + sec/3600.)/d2r # checked the formula
    
    srcs = srcs[ where((Decs_src<87./d2r)*(Decs_src>-87./d2r))[0],:] # Now 3386 srcs
    N_src = len(srcs) 
    print('# Number of srcs:', N_src )
    
    # Get the RAs and Decs in degree
    hr     = array(srcs[:,3], dtype=float)
    minute = array(srcs[:,4], dtype=float)
    sec    = array(srcs[:,5], dtype=float)
    RAs_src = (hr + minute/60. + sec/3600.)/24.*360./d2r # checked the formula
    deg     = array(srcs[:,6], dtype=float);\
            idx_deg_neg = where( char.ljust(srcs[:,6], 1) == '-' )
    minute  = array(srcs[:,7], dtype=float); minute[idx_deg_neg] *= -1
    sec     = array(srcs[:,8], dtype=float); sec[idx_deg_neg] *= -1
    Decs_src = (deg + minute/60. + sec/3600.)/d2r # checked the formula
    
    W_mdls_src = array( srcs[:,19], dtype=float ) 
    
    #exit()
'''
########################### !Radio quasars 15 GHz! ############################


############################## 4LAC to rpdc Hpr ################################
for ii in range(0):
    dat = pf.open('data_input/table_4LAC.fits')[1].data
    RAs_src = dat.field('RAJ2000')/d2r
    Decs_src = dat.field('DEJ2000')/d2r # 2863 _srcs
    eflux100 = dat.field('Energy_Flux100')
    
    class_src = dat.field('Class') 
    #idx =  where( (Decs_src>-87)*(Decs_src<87) )  
    idx = where( (Decs_src>-87/d2r)*(Decs_src<87/d2r)*(class_src!='AGN')
        *(class_src!='NLSY1')
        *(class_src!='RDG')
        *(class_src!='agn')
        *(class_src!='css')
        *(class_src!='nlsy1')
        *(class_src!='rdg')
        *(class_src!='ssrq')
        )
    
    RAs_src  = RAs_src[idx];
    Decs_src = Decs_src[idx];
    eflux100 = eflux100[idx];
    
    W_mdls_src = eflux100
    #print(W_mdls_src)
    #print(W_mdls_src.shape)
    
    N_src = len(RAs_src)
    print('# Number of srcs:', N_src )
    
    
    for i in range(0):
        'To get the #s of each src type.'
        print( unique(class_src) )
        #print( len(where( class_src=='AGN' )[0]) )
        print( len(where( class_src=='BCU' )[0]) )
        print( len(where( class_src=='BLL' )[0]) )
        print( len(where( class_src=='FSRQ' )[0]) )
        #print( len(where( class_src=='NLSY1' )[0]) )
        #print( len(where( class_src=='RDG' )[0]) )
        #print( len(where( class_src=='agn' )[0]) )
        print( len(where( class_src=='bcu' )[0]) )
        print( len(where( class_src=='bll' )[0]) )
        #print( len(where( class_src=='css' )[0]) )
        print( len(where( class_src=='fsrq' )[0]) )
        #print( len(where( class_src=='nlsy1' )[0]) )
        #print( len(where( class_src=='rdg' )[0]) )
        #print( len(where( class_src=='ssrq' )[0]) )
        exit()
############################# !4LAC to rpdc Hpr! ###############################

#################################### 3LAC ######################################
for i in range(0):
    'Copied from likelihood_reproduce_1810.02823.py'
    srcs = loadtxt('data_input/3LAC.dat',dtype=str)
    #srcs = array(srcs[:,0:7], dtype=float)
    # Get the Decs in degree
    deg     = array(srcs[:,4], dtype=float); \
            idx_deg_neg = where( char.ljust(srcs[:,4], 1) == '-' )
    minute  = array(srcs[:,5], dtype=float); minute[idx_deg_neg] *= -1
    sec     = array(srcs[:,6], dtype=float); sec[idx_deg_neg] *= -1
    Decs_src = deg + minute/60. + sec/3600. # checked the formula
    
    srcs = srcs[ where( (Decs_src<87)*(Decs_src>-87) )[0] ]
    N_src = len(srcs) 
    #print N_src  # 1769 correct!!
    # Get the RAs and Decs in degree
    hr     = array(srcs[:,1], dtype=float)
    minute = array(srcs[:,2], dtype=float)
    sec    = array(srcs[:,3], dtype=float)
    RAs_src = ( (hr + minute/60. + sec/3600.)/24.*360. )/d2r # checked the formula
    deg     = array(srcs[:,4], dtype=float)
    minute  = array(srcs[:,5], dtype=float); minute[where(deg < 0)] *= -1
    sec     = array(srcs[:,6], dtype=float); sec[where(deg < 0)] *= -1
    Decs_src = ( deg + minute/60. + sec/3600. )/d2r # checked the formula
    print('There is a bug here and 3LAC, when deg = "-0"!!!!!!!!!!!!!!!!!!!')
    exit()
    
    print('# Number of srcs:', N_src )
################################### !3LAC! #####################################


########################## CHIME FRBs  ###############################
for i in range(0):
    srcs = loadtxt('/Users/beizhou/Dropbox/1acdm/1work_ptnl/20211028_HEnuFRB/data_input/CHIME_FRB_1st_catalog.dat', dtype=str)
    #ppp(srcs[:,3])
    RAs_src = array(srcs[:,3], dtype=float)/d2r
    #print(RAs_src.max(), RAs_src.min())
    Decs_src = array(srcs[:,5], dtype=float)/d2r
    #print(Decs_src.max(), Decs_src.min())
    N_src = len(RAs_src)
    print('# of srcs', len(RAs_src))
    
    #idx = where( (Decs_src>-87./d2r)*(Decs_src<87./d2r) );
    #srcs = srcs[idx]
    #RAs_src = RAs_src[idx]
    #Decs_src = Decs_src[idx]
    #N_src = len(RAs_src)
    #print('# of srcs', len(RAs_src))
    
    #Need: Nsrc; RAs_src in rad; Decs_src in rad;
######################### !CHIME FRBs ! ##############################

for ii in range(0): # Sara sources
    for i in range(0):
        srcs = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20201030_HEnu_radio_quasars/data_input/sources/20220424_Sara.txt', dtype=str)
        RAs_src = array(srcs[:,0], dtype=float)/d2r
        #print(RAs_src.max(), RAs_src.min())
        Decs_src = array(srcs[:,1], dtype=float)/d2r
        #print(Decs_src.max(), Decs_src.min())
        N_src = len(RAs_src)
        print('# Numnber of srcs', len(RAs_src))
    for i in range(0):
        srcs = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20201030_HEnu_radio_quasars/data_input/sources/20220520_sara_blazars.txt', dtype=str)
        RAs_src = array(srcs[:,0], dtype=float)/d2r
        Decs_src = array(srcs[:,1], dtype=float)/d2r
        N_src = len(RAs_src)
        print('# Numnber of srcs', len(RAs_src))
    
    for i in range(0):  # 512 healpix map for Sara.
        # Below is to make the list of RAs and Decs
        import healpy as hp
        NSIDE = 512  #Defines the resolution of the map, e.g. NSIDE=512 corresponds to a resolution of 0.11°
        NPIX = hp.nside2npix(NSIDE) #Number of pixels in the sky map
        indices = arange(NPIX)
        RAs_src, Decs_src = hp.pix2ang(NSIDE,indices,lonlat=True) #Transforms a specific pixel to the corresponding coordinates
        savetxt('ttt.txt', array([RAs_src, Decs_src]).T, fmt='%f')
    
        srcs = loadtxt('data_input/sources/20220629_Sara_healpix512.txt', dtype=str)
        RAs_src = array(srcs[:,0], dtype=float)/d2r
        Decs_src = array(srcs[:,1], dtype=float)/d2r
        N_src = len(RAs_src)
        print('# Numnber of srcs', len(RAs_src))
    
    for i in range(1): # 20230215_Sara_sources_2207.06314
        tmp = loadtxt('data_input/sources/20230215_Sara_sources_2207.06314.txt', dtype=str, delimiter=',')  # (3469, 51)
        print(tmp)
        # first check if the sources are the sources in the ppr
        # then do the stacking analysis.

for i in range(0): # KM AGN srcs
    srcs = loadtxt('data_input/sources/20220425_BASS_DR1_X_ray_tables/catalog_BZ.txt',dtype=str); 
    Decs_src = array(srcs[:,3], dtype=float)/d2r
    srcs = srcs[ where((Decs_src<87./d2r)*(Decs_src>-87./d2r))[0],:] ###!!!
    N_src = len(srcs); print('# Number of srcs:', N_src )

    W_mdls_src = array( srcs[:,7], dtype=float ) 
    srcs = srcs[ where( (W_mdls_src>100) )[0],:] ###!!!
    N_src = len(srcs); print('# Number of srcs:', N_src )
    #print(srcs)

    RAs_src = array(srcs[:,2], dtype=float)/d2r
    Decs_src = array(srcs[:,3], dtype=float)/d2r
    W_mdls_src = array( srcs[:,7], dtype=float ) 
for i in range(0): # KM four blazars
    srcs = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20201030_HEnu_radio_quasars/data_input/sources/20220425_KM.txt', dtype=str)
    RAs_src = array(srcs[:,0], dtype=float)/d2r
    Decs_src = array(srcs[:,1], dtype=float)/d2r
    #print(Decs_src.max(), Decs_src.min())
    N_src = len(RAs_src)
    print('# Numnber of srcs', len(RAs_src))





#backup

# Done
for i in range(0): # Var, referee response
    srcs = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20201110_Var/202011_variabilities_correlations/data_output/Rand5000.txt').T
    RAs_src = srcs[0]/d2r
    Decs_src = srcs[1]/d2r
    N_src = len(RAs_src)
    print('# Numnber of srcs', len(RAs_src))

for i in range(0): # old
    ################################# 3HAWC #################################
    for i in range(0):
        srcs = loadtxt('data_input/3HAWC.dat',dtype=str)
        RAs_src  = array(srcs[:, 4], dtype = float)/d2r
        Decs_src = array(srcs[:, 5], dtype = float)/d2r
        
        srcs = srcs[ where((Decs_src<87./d2r)*(Decs_src>-87./d2r))[0], :]
        RAs_src  = array(srcs[:, 4], dtype = float)/d2r
        Decs_src = array(srcs[:, 5], dtype = float)/d2r
        N_src = len(Decs_src)
        
        print('# Number of srcs:', N_src )
    ################################ !3HAWC! ################################

    ################################ Ranjan srcs #################################
    for i in range(0):
        tmp = loadtxt('data_input/Ranjan_srcs.dat').T
        RAs_src = tmp[0]/d2r
        Decs_src = tmp[1]/d2r
        idx = where( (Decs_src>-87/d2r)*(Decs_src<87/d2r) )
        RAs_src = RAs_src[idx]
        Decs_src = Decs_src[idx]
        N_src = len(RAs_src)
        print('# Number of srcs:', N_src )
    ############################### !Ranjan srcs! ################################

    ############################### Milagro 17 srcs ################################
    # to rpdc the n_s = 7.6 in 1012.2137
    '''
    tmp = loadtxt('data_input/Milagro_17srcs.dat').T
    N_src = tmp.shape[1]
    RAs_src  = tmp[0]/d2r
    Decs_src = tmp[1]/d2r
    print('# Number of srcs:', N_src )
    '''
    ############################## !Milagro 17 srcs! ###############################
    
    ############################### Milagro 6 srcs ################################
    # to rpdc n_s in 1406.6757
    '''
    tmp = loadtxt('data_input/Milagro_6srcs.dat').T
    try: 
        N_src = tmp.shape[1]
    except: # for the case there is only 1 src
        N_src = 1
    RAs_src  = tmp[0]/d2r
    Decs_src = tmp[1]/d2r
    print('# Number of srcs:', N_src )
    '''
    ############################## !Milagro 6 srcs! ###############################
