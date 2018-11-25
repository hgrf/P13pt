import pickle
import os

class FolderInfo(object):
    def initmembers(self, folderinfo=None):
        self.folder = folderinfo.folder if folderinfo is not None else ''
        self.description = folderinfo.description if folderinfo is not None else ''
        self.files = folderinfo.files if folderinfo is not None else dict()

    def __init__(self):
        self.initmembers()

    def load(self, folder):
        '''
        check for mdbinfo file in given folder and load it if available
        '''
        try:
            picklefile = open(os.path.join(folder, 'mdbinfo.pickle'), 'rb')
            folderinfo = pickle.load(picklefile)
            self.initmembers(folderinfo)
            picklefile.close()
        except (IOError, EOFError):  # file does not exist or is empty
            self.initmembers()
        self.folder = folder

    def save(self):
        '''
        save to mdbinfo file
        '''
        picklefile = open(os.path.join(self.folder, 'mdbinfo.pickle'), 'wb')
        pickle.dump(self, picklefile)
        picklefile.close()


class FileInfo(object):
    def __init__(self, description=''):
        self.description = description
        self.modifiers = list()
        self.defaultmod = 0

class Mod(object):
    def __init__(self):
        self.name = ''
        self.code = ''
