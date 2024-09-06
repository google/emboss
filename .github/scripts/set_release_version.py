# Obtains a date-based version for the release workflow.

import datetime

now_utc = datetime.datetime.now(datetime.timezone.utc)
version = now_utc.strftime("%Y.%m%d.%H%M%S")
print("::set-output name=version::v{}".format(version))
