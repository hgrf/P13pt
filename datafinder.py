from glob import glob

def findtextfiles(dirs):
    # create list of all data files in given directory
    f_list = []
    for di in dirs:    
        f_list.extend((glob(di + '/*.txt') + glob(di + '/*/*.txt')))
        
    return f_list
    

def findVg1sweepspectra(dir_sample):
    '''
        find spectra and sort file list by gate voltage
    '''
    f_list = (glob(dir_sample + '/*/S-parameter/*.txt') + glob(dir_sample + '/S-parameter/*.txt'))
    
    # helper function to enable sorting by Vg in filename
    def sorting(name):
        if name.find('Vg1=')!=-1:
            vg = float(name[name.find('Vg1=')+4:
                                    name.find('Vg1=')+12])
        else: 
            vg = float(name[name.find('Vgate=')+6:
                                    name.find('Vgate=')+14])
        if 'return' in name: vg += 1000         # shift up return sweep
        return vg    
    
    # use helper function to sort file list
    f_list = sorted(f_list, key=sorting)
    
    return f_list
    