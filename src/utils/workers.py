"""إدارة عمر خيوط الفحص وتهيئة COM لكل خيط وإبقائه حيًا حتى ينتهي بأمان."""

from PySide6.QtCore import QThread

_workers = set()


def active_workers():
    for worker in list(_workers):
        if worker.isFinished():
            _workers.discard(worker)
    return [worker for worker in _workers if worker.isRunning()]


class ManagedThread(QThread):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        original_run = cls.__dict__.get("run")
        if original_run:

            def run(self):
                com = None
                try:
                    import pythoncom

                    pythoncom.CoInitialize()
                    com = pythoncom
                    original_run(self)
                finally:
                    if com:
                        com.CoUninitialize()

            cls.run = run

    def start(self, *args, **kwargs):
        # المرجع القوي يبقي الخيط حيًا حتى لو استبدلت الصفحة متغير _worker أثناء التحديث.
        active_workers()
        _workers.add(self)
        super().start(*args, **kwargs)
