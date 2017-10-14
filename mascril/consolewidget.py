#!/usr/bin/python
# -*- coding: utf-8 -*-

# Python 2.7

"""
    Adapted from Jean-Paul Vidal (2013)
    http://python.jpvweb.com/mesrecettespython/doku.php?id=pyqt4_console_python
"""
 
import sys, os
import code
from io import BytesIO as StringIO 
from Queue import Queue
 
from PyQt4 import QtCore, QtGui

try:
    from PyQt4.QtCore import QString
except ImportError:
    QString = str
 
#############################################################################
class Interpy(code.InteractiveConsole):
    """Interpréteur Python"""
 
    #========================================================================
    def __init__(self, tlanceur, locals=None, filename="<console>"):
        """initialisation"""
        code.InteractiveConsole.__init__(self, locals=None, filename="<console>")
        self.tlanceur = tlanceur # adresse du thread qui a lancé l'interpréteur
 
        # prépa de l'arrêt d'exécution de l'interpréteur sur demande
        self.stopexecflag = False
 
        # rediriger sur le thread lanceur pour gagner du temps d'exécution
        self.write = self.tlanceur.write
        self.read = self.tlanceur.read
        self.quit = self.tlanceur.quit
 
    #========================================================================
    def runcode(self, code):
        """surcharge de runcode pour rediriger sys.stdout et sys.stderr"""
        # redirection de la sortie d'affichage
        self.std_sav = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = sio = StringIO()
        sio.write = self.write #2 rediriger l'écriture du fichier en RAM: sio
 
        # exécution de l'instruction Python compilée
        try:
            sys.settrace(self.trace) # mise en place du traçage
            exec code in self.locals # exécution du code
            sys.settrace(None) # arrêt du traçage
        except SystemExit:
            sys.settrace(None) # arrêt du traçage
            self.quit() # quitter le programme
        except:
            sys.settrace(None) # arrêt du traçage 
            self.showtraceback() # affichage de l'exception rencontrée
        finally:
            # remettre la sortie d'affichage initiale
            sys.stdout, sys.stderr = self.std_sav
            sio.close()
 
    #========================================================================
    def trace(self, frame, event, arg):
        """méthode appelée à chaque ligne de code exécutée par exec"""
        if event == 'line':
            if self.stopexecflag:
                self.stopexecflag = False
                raise KeyboardInterrupt("Arret d'execution sur demande")
        return self.trace
 
    #========================================================================
    def stopexec(self):
        """ méthode qu'on appelle pour demander l'arrêt de l'exécution"""
        self.stopexecflag = True
 
    #========================================================================
    def raw_input(self, prompt):
        """lire la prochaine ligne d'instruction Python"""
        return self.read(prompt)
 
    #========================================================================
    def write(self, data):
        """(redirigé) affiche data par l'intermédiaire du thread"""
        pass
 
    #========================================================================
    def read(self, prompt):
        """(redirigé) lit la chaine à interpréter par l'intermédiaire du thread"""
        pass
 
    #========================================================================
    def quit(self):
        """(redirigé) ferme l'application par l'intermédiaire du thread"""
        pass
 
#############################################################################
class Tipy(QtCore.QThread):
    """thread Qt qui porte l'interpréteur Python"""
 
    finconsole = QtCore.pyqtSignal()
    pourafficher = QtCore.pyqtSignal(unicode) 
 
    #========================================================================
    def __init__(self, parent=None): 
        super(Tipy, self).__init__(parent)
        # lancement de l'interpréteur Python (argument: l'adresse du thread)
        self.interpy = Interpy(self)
        # initialisation de la pile qui contiendra l'instruction à exécuter
        self.instruction = Queue(maxsize=1)
        # initialisation du drapeau pour synchroniser l'affichage du QTextEdit
        self.okwrite = False
        self.mutexokwrite = QtCore.QMutex()
 
    #========================================================================
    def run(self):
        """partie exécutée en asynchrone: la boucle de l'interpréteur Python"""
        self.interpy.interact()
 
    #========================================================================
    def write(self, data):
        """affiche data en envoyant un message à la fenêtre"""
        # pour être sûr que data est en unicode
        if not isinstance(data, unicode): 
            data = unicode(data)
        # débarrasse data des éventuels fins de ligne des 2 côtés
        while data!=u"" and data[0] in ['\n', '\r']: data = data[1:]
        while data!=u"" and data[-1] in ['\n', '\r']: data = data[:-1]
        if data!=u"":
            # envoie la réponse sous forme de message (avec shake-hand)
            self.mutexokwrite.lock()
            self.okwrite = False
            self.mutexokwrite.unlock()
            # envoie data avec le signal 'pourafficher'
            self.pourafficher.emit(data)
            # attend jusqu'à ce que le message soit effectivement affiché
            while not self.okwrite:
                pass 
 
    #========================================================================
    def read(self, prompt):
        """lit l'instruction Python à interpréter"""
        # envoi l'invite pour affichage
        self.write(prompt)
        # prend l'instruction dans la pile dès qu'il y en a une
        ins = self.instruction.get()
        if not str(ins).startswith('runfile:'):
            return ins
        else:
            filename = ins[8:]
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    self.interpy.runcode(compile(f.read(), filename, 'exec'))
            else:
                self.write('File not found!!')
            return 'pass'
 
    #========================================================================
    def stop(self):
        """appelé quand on veut arrêter l'exécution de l'interpréteur"""
        self.interpy.stopexec()
 
    #========================================================================
    def quit(self):
        """méthode appelée quand on veut fermer l'application"""
        # arrête l'interpréteur s'il est en cours d'exécution
        self.stop()
        # émet le signal de fin pour la fenêtre
        self.finconsole.emit()
 
#############################################################################
class ConsoleWidget(QtGui.QTextEdit):
    """sous-classement de QTextEdit pour communiquer avec l'interpréteur
       Python via un QThread
    """

    # signal pour recevoir du texte à afficher
    pourafficher = QtCore.pyqtSignal(unicode) 
    # signal pour recevoir une demande d'arrêt
    finconsole = QtCore.pyqtSignal()
    # signal pour émettre une demande de fermeture de la fenêtre
    finfenetre = QtCore.pyqtSignal()
 
    #========================================================================
    def __init__(self, parent=None, initpy=u"consolepy_init.py"):
        super(ConsoleWidget, self).__init__(parent)
        # stockage de l'argument passé
        self.initpy = initpy
 
        # prépa de l'initialisation de l'interpréteur si demandé au lancement
        if isinstance(self.initpy, (str, unicode)):
            # si c'est une chaine: elle doit représenter un fichier à charger
            nfc = self.initpy
            self.initpy = []
            if os.path.exists(nfc):
                with open(nfc, 'r') as f:
                    for ligne in f:
                        self.initpy.append(ligne.rstrip())
        else:
            if not isinstance(self.initpy, (list, tuple)):
                # mauvais type pour self.initpy: on n'en tient pas compte
                self.initpy = []
        self.lginitpy = len(self.initpy)
 
        # configuration du QTextEdit
        self.setAcceptRichText(False)
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap) 
        # Changer la police de caractères et sa taille
        font = QtGui.QFont()
        font.setFamily(u"DejaVu Sans Mono")
        font.setPointSize(10)
        self.setFont(font)
 
        # lancement du thread qui porte l'interpréteur Python
        self.tipy = Tipy()
        # prépa pour recevoir de tipy un signal de fermeture de la fenêtre 
        self.tipy.finconsole.connect(self.quitter)
        # prépa pour recevoir de tipy du texte à afficher 
        self.tipy.pourafficher.connect(self.affiche)
        # démarrage du thread
        self.tipy.start()
 
        # initialisation de la position courante du curseur après invite
        self.pos1 = self.textCursor().position()
        # portera la position du curseur à la 1ère invite
        self.pos0 = self.pos1
 
        # initialisation de l'historique des lignes d'instruction Python
        self.historique = []
        self.ih = 0
 
        # compteur du nombre d'invites affichées  
        self.nbinvites = -1

    #========================================================================
    @QtCore.pyqtSlot(unicode)
    def affiche(self, texte):
        """Affiche la chaine 'texte' dans le widget QTextEdit"""
 
        # ajoute la chaine unicode à la fin du QTextEdit
        self.append(texte)
        # déplace le curseur à la fin du texte
        self.moveCursor(QtGui.QTextCursor.End, QtGui.QTextCursor.MoveAnchor)
        # force le rafraichissement pour affichage en temps réel
        QtCore.QCoreApplication.processEvents() 
        # met à jour la position du curseur dans le texte
        self.pos1 = self.textCursor().position()
 
        # renvoie un accusé de réception de fin d'affichage (shake-hand)
        self.tipy.mutexokwrite.lock()
        self.tipy.okwrite = True
        self.tipy.mutexokwrite.unlock()
 
        # envoie les lignes de code d'initialisation après la 1ère invite
        if self.nbinvites < self.lginitpy:
            if self.nbinvites==0:
                # 1ère invite
                self.pos0 = self.textCursor().position() 
            if self.nbinvites>=0:
                # il y a encore des lignes d'instruction initiales à exécuter
                self.tipy.instruction.put(self.initpy[self.nbinvites])
            self.nbinvites += 1

    # =======================================================================
    def keyPressEvent(self, event):
        """traitement des évènements clavier du QTextEdit"""
 
        #--------------------------------------------------------------------
        if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            # touche "retour"
            # déplacer le curseur à la fin du texte si ce n'est pas le cas
            self.moveCursor(QtGui.QTextCursor.End, QtGui.QTextCursor.MoveAnchor)
            # texte situé entre la précédente position du curseur et l'actuelle
            pos1 = self.pos1
            pos2 = self.textCursor().position()
            texte = unicode(self.toPlainText())[pos1:pos2]
            # débarrasse l'instruction 'texte' des éventuels fins de ligne
            while texte!=u"" and texte[0] in ['\n', '\r']: texte = texte[1:]
            texte = texte.rstrip() # retire à droite fin de ligne et espaces
            # empile l'instruction pour qu'elle soit exécutée
            self.tipy.instruction.put(texte)
            # conserver la ligne d'instruction dans l'historique
            if texte != u"":
                self.historique.append(texte)
                self.ih = len(self.historique)-1 # pointe sur le dernier élément
            # sauvegarde la position du curseur de début d'instruction
            self.pos1 = pos2
            event.accept()
 
        #--------------------------------------------------------------------
        elif event.key()==QtCore.Qt.Key_Z and (event.modifiers() & QtCore.Qt.ControlModifier):
            # Ctrl-Z: annule ce qui vient d'être tapé
            event.accept()
            # exécute le Ctrl-Z normal du QTextEdit
            QtGui.QTextEdit.keyPressEvent(self, event)
            # déplace le curseur à la fin du texte
            self.moveCursor(QtGui.QTextCursor.End, QtGui.QTextCursor.MoveAnchor)
            # force le rafraichissement pour affichage en temps réel
            QtCore.QCoreApplication.processEvents() 
            # met à jour la position du curseur dans le texte
            self.pos1 = self.textCursor().position()
            
        #--------------------------------------------------------------------
        elif event.key()==QtCore.Qt.Key_S and \
                         (event.modifiers() & QtCore.Qt.ControlModifier):
            # Ctrl-S arrête l'interpréteur
            self.tipy.stop()            
            event.accept()
 
        #--------------------------------------------------------------------
        elif event.key()==QtCore.Qt.Key_E and \
                         (event.modifiers() & QtCore.Qt.AltModifier):
            # Alt-E remet l'affichage au début à l'emplacement de la 1ère invite
            texte = unicode(self.toPlainText())
            texte = texte[:self.pos0]
            self.clear()
            self.affiche(texte)
            self.pos1 = self.pos0
            event.accept()
 
        #--------------------------------------------------------------------
        elif event.key()==QtCore.Qt.Key_Up:
            # traitement touche flèche en haut: instruction précédente
            if self.historique!=[] and self.ih>=0:
                pos1 = self.pos1
                pos2 = self.textCursor().position()
                instruction = self.historique[self.ih]
                texte = unicode(self.toPlainText())
                texte = texte[:pos1] + instruction + texte[pos2:]
                self.clear()
                self.affiche(texte)
                self.pos1 = pos1
                if self.ih>0:
                    self.ih -= 1
            event.accept()
 
        #--------------------------------------------------------------------
        elif event.key()==QtCore.Qt.Key_Down:
            # traitement touche flèche en bas, instruction suivante
            if self.historique!=[] and self.ih<len(self.historique)-1:
                self.ih += 1
                pos1 = self.pos1
                pos2 = self.textCursor().position()
                instruction = self.historique[self.ih]
                texte = unicode(self.toPlainText())
                texte = texte[:pos1] + instruction + texte[pos2:]
                self.clear()
                self.affiche(texte)
                self.pos1 = pos1
            event.accept()
 
        #--------------------------------------------------------------------
        elif event.key()==QtCore.Qt.Key_Backspace:
            # empêche le backspace de revenir sur l'invite
            pos = self.textCursor().position()
            if pos>self.pos1:
                event.ignore()
                # évènement transmis à l'ancêtre
                QtGui.QTextEdit.keyPressEvent(self, event)
            else:
                event.accept()    
 
        #--------------------------------------------------------------------
        elif event.key()==QtCore.Qt.Key_Tab:
            """Tabulation: insérer 4 espaces à l'emplacement du curseur"""
            self.insertPlainText(u"    ")
 
        #--------------------------------------------------------------------
        elif event.key() in [QtCore.Qt.Key_Up, 
                             QtCore.Qt.Key_Down,
                             QtCore.Qt.Key_PageUp, 
                             QtCore.Qt.Key_PageDown]:
            """neutralisation de touches de QTextEdit inutile pour 
               l'interpréteur
            """
            event.accept() 
 
        #--------------------------------------------------------------------
        else:
            # n'importe quel autre caractère que ceux ci-dessus
            event.ignore()
            # évènement transmis à l'ancêtre QTextEdit
            QtGui.QTextEdit.keyPressEvent(self, event)
 
    #========================================================================
    @QtCore.pyqtSlot()
    def quitter(self):
        """la fenêtre a reçu le signal de fermeture de l'interpréteur """
        # on ré-émet le signal de fermeture pour la fenêtre
        #self.emit(QtCore.SIGNAL("finfenetre()"))
        self.finfenetre.emit()