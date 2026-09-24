using System;
using System.Diagnostics;
using System.IO;
using System.Collections.Generic;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

// Calls only the input dispatch helper with an injected recorder, never Steam or a real process.
static class LaunchInputHarness
{
    static int checks;
    static void Check(bool value, string description)
    {
        if (!value) throw new Exception(description);
        checks++;
        Console.WriteLine("PASS: " + description);
    }

    static object Field(object owner, string name) { return owner.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic).GetValue(owner); }
    static void ActivateWithoutShowing(Form form) { typeof(Form).GetMethod("OnActivated", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(form, new object[] { EventArgs.Empty }); }

    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            string game = Path.GetFullPath(args[0]);
            Directory.CreateDirectory(Path.Combine(game, "InputLab"));
            string components = Path.Combine(game, Cfg.ComponentsFile);
            string controls = Path.Combine(game, @"InputLab\DOA5LR-Commandes.exe");
            string profile = Path.Combine(game, "DOA5LR-InputBridge.ini");
            string config = "# retain this comment\r\ninputlab=1\r\nborderless=0\r\n60fps=1\r\n";
            File.WriteAllText(components, config, Encoding.UTF8);
            File.WriteAllText(profile, "[Input]\r\nMode=Keyboard\r\n[Keyboard]\r\n37=33\r\n", Encoding.UTF8);
            byte[] beforeComponents = File.ReadAllBytes(components), beforeProfile = File.ReadAllBytes(profile);
            int opened = 0;
            ProcessStartInfo request = null;
            Action<ProcessStartInfo> record = info => { opened++; request = info; };

            // The public 0.3.8 manifest does not list InputLab, but the locally installed component does.
            Component.Current = Component.Defaults;
            Check(InputLauncher.Enabled(game), "saved ON still routes to InputLab with an old manifest");
            bool missingBlocked = false;
            try { InputLauncher.TryOpen(game, record); }
            catch (FileNotFoundException ex) { missingBlocked = ex.FileName == controls && ex.Message.Contains("Repair"); }
            Check(missingBlocked && opened == 0, "missing Controls app blocks launch with repair guidance");

            File.WriteAllText(controls, "non executable test fixture");
            Check(InputLauncher.TryOpen(game, record) && opened == 1, "ON opens the input chooser exactly once");
            Check(request.FileName == controls && request.WorkingDirectory == Path.GetDirectoryName(controls), "chooser is the app inside the selected game folder");
            Check(request.Arguments == "" && request.UseShellExecute, "chooser receives no auto-play arguments");
            Check(Convert.ToBase64String(beforeComponents) == Convert.ToBase64String(File.ReadAllBytes(components)) &&
                  Convert.ToBase64String(beforeProfile) == Convert.ToBase64String(File.ReadAllBytes(profile)), "routing preserves installed choices and custom F mapping byte for byte");

            File.WriteAllText(profile, "[Input]\r\nMode=Controller\r\n");
            Check(InputLauncher.TryOpen(game, record) && opened == 2, "Controller mode also opens the chooser before play");
            bool failurePropagated = false;
            try { InputLauncher.TryOpen(game, info => { throw new IOException("test launch failure"); }); }
            catch (IOException ex) { failurePropagated = ex.Message == "test launch failure"; }
            Check(failurePropagated, "an app launch failure is not reported as the normal Steam route");

            File.WriteAllText(components, "inputlab=0\r\n");
            Check(InputLauncher.Available(game) && InputLauncher.TryOpen(game, record) && opened == 3,
                  "runtime OFF still opens installed core settings app");
            File.Delete(components);
            Check(InputLauncher.TryOpen(game, record) && opened == 4, "installed app always opens before play without changing runtime selection");
            File.Delete(controls);
            Check(!InputLauncher.TryOpen(game, record) && opened == 4, "legacy pack without app or InputLab choice retains normal Steam route");
            File.WriteAllText(components, "inputlab=0\r\n");
            missingBlocked = false;
            try { InputLauncher.TryOpen(game, record); }
            catch (FileNotFoundException) { missingBlocked = true; }
            Check(missingBlocked && opened == 4, "missing app blocks silent Steam bypass even with runtime OFF");
            File.Delete(components);
            Component.Current = new[] { Component.InputLab };
            missingBlocked = false;
            try { InputLauncher.TryOpen(game, record); }
            catch (FileNotFoundException) { missingBlocked = true; }
            Check(missingBlocked && opened == 4, "InputLab-capable manifest requires chooser before initial install");
            Check(!InputLauncher.TryOpen("", record) && opened == 4, "no game folder does not open the chooser");

            File.WriteAllText(Path.Combine(game, "game.exe"), "fake game");
            File.WriteAllText(controls, "non executable test fixture");
            File.WriteAllText(components, "inputlab=0\r\n");
            using (var form = new MainForm(false))
            {
                ((TextBox)Field(form, "txtGame")).Text = game;
                var finder = (Button)Field(form, "btnFinder");
                var choices = (List<CheckBox>)Field(form, "chkComp");
                Check(finder.Enabled && !choices[0].Checked, "Keyboard / controller button stays enabled with runtime unchecked");
                File.WriteAllText(components, "inputlab=1\r\n");
                ActivateWithoutShowing(form);
                Check(choices[0].Checked, "returning to installer reflects runtime activation by Controls");
                choices[0].Checked = false;
                ActivateWithoutShowing(form);
                Check(!choices[0].Checked, "returning focus preserves pending user component changes");
                File.Delete(controls);
                ActivateWithoutShowing(form);
                Check(!finder.Enabled, "missing settings app disables its button independently of runtime checkbox");
            }
            Console.WriteLine("All " + checks + " input launch routing checks passed. No processes were started.");
            return 0;
        }
        catch (Exception ex) { Console.Error.WriteLine(ex); return 1; }
    }
}
