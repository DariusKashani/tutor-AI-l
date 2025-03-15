# Logs Directory

This directory contains log files for the Math Tutorial Generator project.

## Contents

- `app.log`: Main application logs
- `api.log`: API endpoint logs
- `task_manager.log`: Task management logs
- `video_generator.log`: Video generation logs
- `script_generator.log`: Script generation logs
- `manim_generator.log`: Manim animation generation logs

## Log Rotation

Log files are not automatically rotated. For production use, consider implementing log rotation to prevent log files from growing too large.

## Viewing Logs

You can view logs using standard Unix tools:

```bash
# View the last 50 lines of the app log
tail -n 50 logs/app.log

# Follow the app log in real-time
tail -f logs/app.log

# Search for errors in all logs
grep "ERROR" logs/*.log
``` 