filename = '/home/hgraef/PhD/Measurements/PRC-TopGate-D3/2018.01.15_VNA_RT/spectrumfitter_3p.txt'
newfile = filename[:-4]+'_HolgersPC.txt'
oldroot = 'C:/Users/David/ownCloud'
newroot = '/home/hgraef/ownCloud/PhD/Measurements'

def rebase(path):
    if not path.startswith(oldroot):
        raise Exception('Root not found in path')
    path = newroot+path[len(oldroot):]
    return path.replace('\\', '/')

with open(filename, 'r') as fin:
    with open(newfile, 'w') as fout:
        for line in fin:
            line = line.strip()
            if line:
                if line[0] == '#':  # line is a comment line
                    line = line[1:].strip()
                    if line.startswith('thru:'):
                        thru = line[5:].strip()
                        fout.write('# thru: '+rebase(thru))
                    elif line.startswith('dummy:'):
                        dummy = line[6:].strip()
                        fout.write('# dummy: '+rebase(dummy))
                    elif line.startswith('dut:'):
                        dut = line[4:].strip()
                        fout.write('# dut: '+rebase(dut))
                    else:
                        fout.write('# '+line)
                else: # line is a data line
                    filename = line.split('\t')[0]
                    fout.write(rebase(filename)+line[len(filename):])
                fout.write('\r\n')