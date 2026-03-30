import pandas as pd
import uuid

df = pd.read_csv('C:\\Users\\spaceman\\Downloads\\db.csv')

# เติม UUID เฉพาะ row ที่ว่าง
df['barcode_uuid'] = df['barcode_uuid'].apply(
    lambda x: str(uuid.uuid4()) if pd.isna(x) or x == '' else x
)

df.to_csv('C:\\Users\\spaceman\\Downloads\\db_fixed.csv', index=False, encoding='utf-8-sig')
