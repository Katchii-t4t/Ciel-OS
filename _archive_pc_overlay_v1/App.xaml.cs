using System.Windows;

namespace Ciel;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        // NB: WallpaperWindow (levande bakgrunn via WorkerW) er parkert — WPF renderar
        // ikkje innhald påliteleg i WorkerW-laget på dette oppsettet (svart desktop).
        // Bakgrunn kan setjast manuelt; Ciel rører den ikkje no.
        new OverlayWindow().Show();     // alltid-tilstades hjørne-orb
    }
}
