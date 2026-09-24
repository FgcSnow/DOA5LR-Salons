using System;
using System.IO;

// Build with Installer.cs and /main:RestoreHarness so tests exercise the actual restore engine.
class RestoreHarness
{
    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            if (args.Length == 3 && args[0] == "--missing")
            {
                Manifest.Parse(File.ReadAllText(args[2]));
                foreach (var rel in Util.MissingRequired(args[1])) Console.WriteLine(rel);
                return 0;
            }
            if (args.Length != 2) return 2;
            new Engine { Game = args[0] }.Restore(args[1]);
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            return 1;
        }
    }
}
