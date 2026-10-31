from pncp.transformacao import ler_json, criar_dataframes

dados = ler_json()

df_atas, df_itens, df_resultados = criar_dataframes(dados)

print("\n=== COLUNAS DAS ATAS ===")
print(df_atas.columns.tolist())

print("\n=== COLUNAS DOS ITENS ===")
print(df_itens.columns.tolist())

print("\n=== COLUNAS DOS RESULTADOS ===")
print(df_resultados.columns.tolist())

print("\n=== EXEMPLO DE ATA ===")
print(df_atas.iloc[0].to_dict())

print("\n=== EXEMPLO DE ITEM ===")
print(df_itens.iloc[0].to_dict())

print("\n=== EXEMPLO DE RESULTADO ===")
print(df_resultados.iloc[0].to_dict())

print("\n=== EXEMPLO DE ATA ===")
print(df_atas.iloc[0].to_dict())