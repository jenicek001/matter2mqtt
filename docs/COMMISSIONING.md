# Commissioning (Web UI First)

This project uses the Python Matter Server Web UI as the primary commissioning method. For Thread devices, you will need the Thread dataset from OTBR.

## Get the Thread Dataset

Run this on the host:

```bash
docker exec otbr ot-ctl dataset active -x
```

Copy the full hex string. You will paste it into the Web UI when prompted.

## Commission via Web UI (Recommended)

1. Open the Web UI:
   - http://localhost:5580
2. Click "Commission Device".
3. Put the device in pairing mode (factory reset if needed).
4. Paste the Thread dataset from the command above.
5. Enter the pairing code from the device label.

### IKEA Pairing Code Note

IKEA labels often show a code like `MT:12345678901`. Enter only the digits, with no dashes or spaces.

## Verify

- Device appears in the Web UI "Nodes" list.
- MQTT data starts flowing:
  ```bash
  mosquitto_sub -t 'matter/#' -v
  ```

