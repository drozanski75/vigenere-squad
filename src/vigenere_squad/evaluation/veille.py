"""Empêche la mise en veille du système pendant une longue évaluation, sans
modifier les réglages de l'utilisateur (effet limité à la durée du calcul).

* Windows : SetThreadExecutionState (le PC reste éveillé, l'écran peut s'éteindre) ;
* macOS : commande `caffeinate -i` attachée au processus ;
* Linux : rien (les sessions de calcul ne se mettent généralement pas en veille).
"""

from __future__ import annotations

import os
import platform
import subprocess
from contextlib import contextmanager

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


@contextmanager
def pas_de_veille():
    systeme = platform.system()
    proc = None
    if systeme == "Windows":
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    elif systeme == "Darwin":
        try:
            proc = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        except OSError:
            proc = None
    try:
        yield
    finally:
        if systeme == "Windows":
            import ctypes

            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        elif proc is not None:
            proc.terminate()
