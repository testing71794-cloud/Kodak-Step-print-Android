"""
Maestro execution stack (Stack A).

- ``run_parallel_devices`` — multi-device / flows-file orchestration with blocking Maestro subprocesses.
- ``atp_jenkins_orchestrator`` — Jenkins ATP folder runs via blocking ``run_one_flow_on_device.bat`` (reports/status preserved).
- ``maestro_runner`` — lifecycle logging, pre-run hygiene, blocking bat invocation helpers.
"""
