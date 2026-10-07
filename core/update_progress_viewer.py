"""A detached Windows progress window that survives replacing the app bundle."""

from __future__ import annotations

from pathlib import Path


def windows_progress_script(state_file: Path, config_dir: Path, version: str) -> str:
    """Render a read-only WPF watcher for the updater's persistent state file."""

    def literal(value: str | Path) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    return (
        f"$stateFile = {literal(state_file)}\n"
        f"$settingsFile = {literal(config_dir / 'app_runtime.json')}\n"
        f"$targetVersion = {literal(version)}\n"
        + r'''
try {
    Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase
    [xml]$layout = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="WizZ Desktop" Width="430" Height="195"
        WindowStartupLocation="CenterScreen" ResizeMode="NoResize"
        Background="#111827" ShowInTaskbar="True">
  <Border Padding="24">
    <StackPanel>
      <TextBlock Text="WizZ Desktop" Foreground="#F9FAFB"
                 FontFamily="Segoe UI" FontSize="20" FontWeight="SemiBold"/>
      <TextBlock Name="StatusText" Text="Preparing the update..."
                 Margin="0,12,0,12" Foreground="#D1D5DB"
                 FontFamily="Segoe UI" FontSize="13" TextWrapping="Wrap"/>
      <ProgressBar Name="Progress" Height="9" IsIndeterminate="True"
                   Foreground="#5B8DEF" Background="#28354B"/>
      <TextBlock Name="HintText" Text="WizZ will restart automatically."
                 Margin="0,12,0,0" Foreground="#9CA3AF"
                 FontFamily="Segoe UI" FontSize="11"/>
    </StackPanel>
  </Border>
</Window>
'@
    $reader = New-Object System.Xml.XmlNodeReader($layout)
    $window = [System.Windows.Markup.XamlReader]::Load($reader)
    $statusText = $window.FindName('StatusText')
    $hintText = $window.FindName('HintText')
    $progress = $window.FindName('Progress')
    $spanish = $false
    try {
        $settings = Get-Content -LiteralPath $settingsFile -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json
        $spanish = [string]$settings.language -eq 'es'
        if ([string]$settings.language -eq 'system') {
            $spanish = (Get-Culture).TwoLetterISOLanguageName -eq 'es'
        }
    } catch { }
    $window.Title = if ($spanish) { 'Actualizador de WizZ Desktop' } else { 'WizZ Desktop updater' }
    $statusText.Text = if ($spanish) { 'Preparando la actualización...' } else { 'Preparing the update...' }
    $hintText.Text = if ($spanish) { 'WizZ se reiniciará automáticamente.' } else { 'WizZ will restart automatically.' }
    $script:closeAt = $null
    $script:seenRestarting = $false
    $script:expiresAt = [DateTime]::UtcNow.AddMinutes(10)
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromMilliseconds(250)
    $timer.Add_Tick({
        if ($script:closeAt -and [DateTime]::UtcNow -ge $script:closeAt) {
            $window.Close()
            return
        }
        if ([DateTime]::UtcNow -ge $script:expiresAt) {
            $window.Close()
            return
        }
        try {
            $state = Get-Content -LiteralPath $stateFile -Raw -ErrorAction Stop | ConvertFrom-Json
            $phase = [string]$state.state
            $detail = [string]$state.detail
            if ($phase -eq 'succeeded') {
                $progress.IsIndeterminate = $false
                $progress.Value = 100
                $statusText.Text = if ($spanish) { "Actualización a v$targetVersion completada." } else { "Update to v$targetVersion complete." }
                if (-not $script:closeAt) { $script:closeAt = [DateTime]::UtcNow.AddSeconds(3) }
            } elseif ($phase -eq 'failed') {
                $progress.IsIndeterminate = $false
                $progress.Value = 0
                $statusText.Text = if ($spanish) { 'No se pudo actualizar. La instalación anterior sigue disponible.' } else { 'Update failed. The previous installation is still available.' }
                $hintText.Text = if ($spanish) { 'Revisa el registro de actualización para más detalles.' } else { 'Check the update log for details.' }
                if (-not $script:closeAt) { $script:closeAt = [DateTime]::UtcNow.AddSeconds(15) }
            } elseif ($phase -eq 'restarting') {
                $script:seenRestarting = $true
                $statusText.Text = if ($spanish) { 'Reiniciando WizZ Desktop...' } else { 'Restarting WizZ Desktop...' }
            } elseif ($detail -like '*Extracting*') {
                $statusText.Text = if ($spanish) { 'Extrayendo la nueva versión...' } else { 'Extracting the new version...' }
            } elseif ($detail -like '*Replacing*') {
                $statusText.Text = if ($spanish) { 'Instalando los archivos nuevos...' } else { 'Installing the new files...' }
            } elseif ($phase -eq 'applying') {
                $statusText.Text = if ($spanish) { 'Esperando a que WizZ se cierre...' } else { 'Waiting for WizZ to close...' }
            } else {
                $statusText.Text = if ($spanish) { 'Preparando la actualización...' } else { 'Preparing the update...' }
            }
        } catch {
            # A successful new instance may consume and remove the state file
            # before this window observes the final "succeeded" state.
            if ($script:seenRestarting -and -not (Test-Path -LiteralPath $stateFile)) {
                $progress.IsIndeterminate = $false
                $progress.Value = 100
                $statusText.Text = if ($spanish) { "Actualización a v$targetVersion completada." } else { "Update to v$targetVersion complete." }
                if (-not $script:closeAt) { $script:closeAt = [DateTime]::UtcNow.AddSeconds(3) }
            }
        }
    })
    $timer.Start()
    [void]$window.ShowDialog()
    $timer.Stop()
} catch {
    # The visual aid must never prevent the update helper from proceeding.
    exit 0
}
'''
    )


__all__ = ["windows_progress_script"]
