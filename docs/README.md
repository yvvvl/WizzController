# Documentation / Documentación

The [English](../README.md) and [Spanish](../README.es.md) repository home pages
give a short overview. The detailed guides live here so release instructions do
not crowd the home page. / Las portadas del repositorio son breves; las guías
detalladas viven aquí.

| Topic / Tema | English | Español |
| --- | --- | --- |
| Install, update, and uninstall / Instalar, actualizar y desinstalar | [Installation](installation.md) | [Instalación](installation.es.md) |
| Manual release checks / Pruebas manuales de release | [Release validation](release-validation.md) | [Validación de release](release-validation.es.md) |
| Source setup, tests, and builds / Desarrollo | [Development](development.md) | [Desarrollo](development.es.md) |
| Local routine schedules / Horarios locales | [Guide](local-routine-schedules.md) | [Guía](local-routine-schedules.es.md) |
| Reactive logo / Logo reactivo | [Guide](reactive-logo.md) | [Guía](reactive-logo.es.md) |

Additional maintainer references:

- [Contributing](../CONTRIBUTING.md) and [repository boundaries](repository-maintenance.md).
- [ARM64 emulation from Windows](arm64-emulation.md).
- [Qt interface capability audit](qt-ui-parity-audit.md). This replaces the
  obsolete migration checklist; it is not a list of current missing features.
- [Legacy Flet retirement audit](legacy-flet-retirement.md): removed code,
  retained data migration, and verification boundaries.
- [Architecture decisions](adr/) and [third-party integration reviews](third-party/).
- [Changelog](../CHANGELOG.md) and [third-party notices](../THIRD_PARTY_NOTICES.md).

The supported desktop UI and release packages use `qt_ui/`. Legacy Flet user
data migration remains supported; see [development](development.md#current-source-paths).
