"""
OpenDEP Compute: import, convert and fit dielectrophoresis spectra.

    python main.py [<project.odcproject>]
    python main.py --self-test [--self-test-data=<spectrum file> --self-test-output=<folder>]   (build check)
"""
import sys

# Keep the last console and log lines in memory for bug reports (Report bug window); before anything prints
from src.diagnostics.bug_reports import install_output_buffer
install_output_buffer()

from PyQt6.QtCore import QEvent, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui import theme  # noqa: E402
from ui.bug_report_dialog import install_crash_handler  # noqa: E402
from ui.main_window import APP_NAME, MainWindow  # noqa: E402


def _arg(name: str) -> str | None:
    return next((a.split('=', 1)[1] for a in sys.argv if a.startswith(f'--{name}=')), None)


def self_test(app: QApplication, data: str | None, output: str | None) -> int:
    """
    Build check of the frozen program: the window opens; with data and an output folder, a spectrum is imported
    into a new project, fitted, and its figure (PNG, SVG, PDF) and PDF report are written; the user guide opens.

    Returns:
        int: Exit code (0 = everything worked).
    """
    from PyQt6.QtCore import QSettings
    from ui.context import AppContext
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, 'OpenDEP', 'Compute-selftest')
    window = MainWindow(AppContext(settings=settings))
    window.show()
    app.processEvents()
    try:
        if data is None or output is None:
            QTimer.singleShot(1500, app.quit)
            return app.exec()
        return _self_test_fit(app, window, data, output)
    finally:
        _destroy(window)


def _self_test_fit(app: QApplication, window: MainWindow, data: str, output: str) -> int:
    """The self-test's import, fit, figure, report and user-guide check (see self_test)."""
    from pathlib import Path
    import traceback
    try:
        from src.fitting.engine import FitSettings, fit_spectra
        from src.formats import read_file
        from src.project.project import Project
        from src.report.report import FitReport, fit_figure, save_figure, write_fit_report
        from src.fitting.engine import fit_summary
        from dataclasses import asdict
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        project = Project.create(out / 'project.odcproject', 'Self-test')
        project.add_import(read_file(data))
        project.save()
        spectra = [e.spectrum for e in project.spectra.values()][:1]
        fs = FitSettings('single_shell', {}, ['eps_mem', 'sigma_cyto'])
        result = fit_spectra(spectra, fs)
        for ext in ('png', 'svg', 'pdf'):
            save_figure(fit_figure(spectra, result.model, result.values, result.scales), out / f'figure.{ext}')
        write_fit_report(FitReport('Self-test', spectra, asdict(fs), fit_summary(result)), out / 'report.pdf')
        window.show_help()
        app.processEvents()
        if 'Quick start' not in window.help_window.browser.toPlainText():
            raise RuntimeError('user guide not found')
        (out / 'ok.txt').write_text(f'R2 {result.r_squared:.4f}', encoding='utf-8')
        return 0
    except Exception:                                   # reported to the smoke test, which fails the build
        traceback.print_exc()
        (Path(output) / 'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        return 1


def _destroy(window: MainWindow) -> None:
    """
    Destroy the window while the QApplication still exists.

    Left to the interpreter's exit, the window (kept alive by reference cycles of its signal connections) and the
    application were destroyed in random order, and the finished process sometimes crashed with an access
    violation (about 1 run in 4; same fix as OpenDEP Neuralnet). No close() here: closeEvent already ran, or must
    not run after the event loop ended.
    """
    import gc
    window.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)   # delete it now, not at exit
    gc.collect()


def main() -> int:
    """
    Start the desktop application.

    Returns:
        int: Exit code.
    """
    if sys.platform == 'win32':                         # own taskbar entry and icon (not Python's when run from source)
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('OpenDEP.Compute')
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName('OpenDEP')
    theme.apply(app)
    if '--self-test' in sys.argv:
        return self_test(app, _arg('self-test-data'), _arg('self-test-output'))
    window = MainWindow()
    window.show()
    install_crash_handler(window.show_bug_report_for_error)   # unhandled errors open Report bug, error filled in
    project = next((a for a in sys.argv[1:] if not a.startswith('-')), None)
    if project:                                         # a project file double-clicked (file association)
        window.open_project(project)
    code = app.exec()
    _destroy(window)
    del window
    return code


if __name__ == '__main__':
    sys.exit(main())
