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
    conda_prefix = result['active_prefix']
    print('Detected conda prefix:', conda_prefix)

    script_path = os.path.dirname(os.path.realpath(__file__))
    print('Current script location:', script_path)

    mdb_script = os.path.join(script_path, 'mdb', 'mdb.py')
    spectrumfitter_script = os.path.join(script_path, 'spectrumfitter', 'spectrumfitter.py')
    mascril_script = os.path.join(script_path, 'mascril', 'mascril.py')
    graphulator_script = os.path.join(script_path, 'graphulator', 'graphulator.py')

    mdb_icon = os.path.join(script_path, 'mdb', 'kmplot-2.ico')
    spectrumfitter_icon = os.path.join(script_path, 'spectrumfitter', 'audacity.ico')
    mascril_icon = os.path.join(script_path, 'mascril', 'tools-wizard.ico')
    graphulator_icon = os.path.join(script_path, 'graphulator', 'calculator.ico')

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
                                   (graphulator_script, graphulator_icon, 'Graphulator')]:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(os.path.join(os.environ['USERPROFILE'], 'Desktop',
                                                         name + '.lnk'))
            shortcut.Targetpath = os.path.join(conda_prefix, 'pythonw.exe')
            shortcut.Arguments = script
            shortcut.IconLocation = icon
            shortcut.WindowStyle = 1  # 7 - Minimized, 3 - Maximized, 1 - Normal
            shortcut.save()
    else:
        print('Cannot create links for your system: ' + platform.system())


if __name__ == '__main__':
    main()
