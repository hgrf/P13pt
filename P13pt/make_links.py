from __future__ import print_function
import os
import json
import subprocess
import platform

if platform.system() == 'Windows':
    import win32com.client


def main():
    try:
        result = subprocess.check_output(['conda', 'info', '--json'])
    except IOError:
        print('Conda could not be found')
        return

    result = json.loads(result)
    conda_root = result['root_prefix']
    conda_prefix = result['active_prefix']
    conda_prefix_name = result['active_prefix_name']
    conda_version = result['conda_version']
    print('Detected conda prefix:', conda_prefix)

    script_path = os.path.dirname(os.path.realpath(__file__))
    print('Current script location:', script_path)

    mdb_script = os.path.join(script_path, 'mdb', 'mdb.py')
    spectrumfitter_script = os.path.join(script_path, 'spectrumfitter', 'spectrumfitter.py')
    mascril_script = os.path.join(script_path, 'mascril', 'mascril.py')
    graphulator_script = os.path.join(script_path, 'graphulator', 'graphulator.py')
    sscalign_script = os.path.join(script_path, 'sscalign', 'sscalign.py')

    mdb_icon = os.path.join(script_path, 'mdb', 'kmplot-2.ico')
    spectrumfitter_icon = os.path.join(script_path, 'spectrumfitter', 'audacity.ico')
    mascril_icon = os.path.join(script_path, 'mascril', 'tools-wizard.ico')
    graphulator_icon = os.path.join(script_path, 'graphulator', 'calculator.ico')
    sscalign_icon = os.path.join(script_path, 'mdb', 'kmplot-2.ico')

    # check for existence of these files
    for f in [mdb_script, spectrumfitter_script, mascril_script, graphulator_script, mdb_icon, spectrumfitter_icon,
              mascril_icon, graphulator_icon]:
        if not os.path.exists(f) or not os.path.isfile(f):
            raise Exception('File ' + f + ' not found')

    # check platform and create link
    if platform.system() == 'Windows':
        for script, icon, name in [(mdb_script, mdb_icon, 'Mercury Data Browser'),
                                   (spectrumfitter_script, spectrumfitter_icon, 'SpectrumFitter'),
                                   (mascril_script, mascril_icon, 'MAScriL'),
                                   (graphulator_script, graphulator_icon, 'Graphulator'),
                                   (sscalign_script, sscalign_icon, 'sscAlign')]:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(os.path.join(os.environ['USERPROFILE'], 'Desktop',
                                                         name + '.lnk'))
            shortcut.Targetpath = os.path.join(conda_root, 'pythonw.exe')
            # the following approach is adapted from how the Spyder shortcut works on Anaconda installations on Windows
            # cwp.py will set up the environment variables (important so that required DLLs can be found)
            # TODO: does this work if any of the paths contains spaces?
            shortcut.Arguments = os.path.join(conda_root, 'cwp.py')+' '+conda_prefix+' '+os.path.join(conda_prefix, 'pythonw.exe')+' '+script
            shortcut.IconLocation = icon
            shortcut.WindowStyle = 1  # 7 - Minimized, 3 - Maximized, 1 - Normal
            shortcut.save()
    elif platform.system() == 'Linux':
        # check conda version is compatible with the way we activate the environment (circumventing the implementation
        # in ~/.bashrc, which is not used when we call the script via bash -c ...)
        maj, min, patch = map(int, conda_version.split('.', 3))
        if not (maj >= 4 and (maj > 4 or min >= 4)):    # version should be >= 4.4
            print('Cannot create links for your conda version, please use conda >= 4.4')
        else:
            for script, icon, link_name, name in [
                (mdb_script, mdb_icon, 'mdb', 'Mercury Data Browser'),
                (spectrumfitter_script, spectrumfitter_icon, 'spectrumfitter', 'SpectrumFitter'),
                (mascril_script, mascril_icon, 'mascril', 'MAScriL'),
                (graphulator_script, graphulator_icon, 'graphulator', 'Graphulator'),
                (sscalign_script, sscalign_icon, 'sscalign', 'sscAlign')]:
                link_folder = os.environ['HOME']+'/.local/share/applications/'
                with open(link_folder+link_name+'.desktop', 'w') as link_file:
                    link_file.write("""
[Desktop Entry]
Type=Application
Terminal=false
Exec=bash -c ". {}/etc/profile.d/conda.sh && conda activate {} && python {}"
Name={}
Icon={}
                    """.format(conda_root, conda_prefix_name, script, name, icon))
    else:
        print('Cannot create links for your system: ' + platform.system())


if __name__ == '__main__':
    main()
