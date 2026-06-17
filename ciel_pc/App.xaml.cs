using System.Windows;

namespace Ciel;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        new WallpaperWindow().Show();   // levande orb bak ikona
        new OverlayWindow().Show();     // alltid-tilstades hjørne-orb
    }
}
