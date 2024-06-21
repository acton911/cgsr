import sys
sys.path.append(r'C:\Program Files (x86)\Qualcomm\QUTS\Support\python')

import QutsClient  # noqa # pylint: disable=E0401

for i in range(10086):
    quts_client = QutsClient.QutsClient("Sample")
    device_manager = quts_client.getDeviceManager()
    device_manager.getDeviceList()
    print(quts_client)

    del quts_client
    import time
    time.sleep(0.1)
