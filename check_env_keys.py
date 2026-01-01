from pathlib import Path
text = Path("/opt/quant_system_clean/google-cloud-trading-system/oanda_config.env").read_text()
for line in text.splitlines():
    if line.startswith("MARKETAUX_KEYS="):
        value = line.split("=", 1)[1].strip().strip("\"")
        print("MARKETAUX_KEYS value length:", len(value))
