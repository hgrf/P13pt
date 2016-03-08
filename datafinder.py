from glob import glob

def findtextfiles(dirs):
    # create list of all data files in given directory
    f_list = []
    for di in dirs:    
        f_list.extend((glob(di + '/*.txt') + glob(di + '/*/*.txt')))
        
    return f_list