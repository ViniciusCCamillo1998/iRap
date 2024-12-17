import pandas as pd
from math import ceil
import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox


def SeparaDF (df, length_min, args):
    # Criar uma lista de dataframes separados
    dfs_separados = []
    df_atual = pd.DataFrame()

    # Armazena valores da primeira linha em um dicionário
    line_values = {}
    for column in args:
        line_values[column] = (df[column][0])

    # Iterar sobre as linhas do dataframe original
    for index, row in df.iterrows():
        # Verificar se a linha está igual
        for column in args:
            if line_values[column] == df[column][index]:
                line_verification = True
            else:
                line_verification = False
                break

        if line_verification:
            # Adicionar a linha atual ao dataframe atual
            df_atual = pd.concat([df_atual, df.loc[[index]]], ignore_index=True)
        else:
            # Adicionar o dataframe atual à lista de dataframes separados
            if not df_atual.empty:
                if df_atual['Length'].sum() >= length_min:
                    dfs_separados.append(df_atual)
                    df_atual = pd.DataFrame()
                    df_atual = pd.concat([df_atual, df.loc[[index]]], ignore_index=True)

                # Verificando comprimentos mínimos
                elif (df_atual['Length'].sum() < length_min):
                    if (df_atual['Section'].iloc[-1] == df['Section'][index]):
                        df_atual = pd.concat([df_atual, df.loc[[index]]], ignore_index=True)
                    elif (df_atual['Section'].iloc[-1] == dfs_separados[-1]['Section'].iloc[-1]):
                        dfs_separados[-1] = pd.concat([dfs_separados[-1], df_atual], ignore_index=True)
                        df_atual = pd.DataFrame()
                        df_atual = pd.concat([df_atual, df.loc[[index]]], ignore_index=True)
                    else:
                        dfs_separados.append(df_atual)
                        df_atual = pd.DataFrame()
                        df_atual = pd.concat([df_atual, df.loc[[index]]], ignore_index=True)
        
        # Armazena valores para próxima interação
        for column in args:
            line_values[column] = (df[column][index])

    # Adicionar o último dataframe atual à lista de dataframes separados
    if not df_atual.empty:
        if (df_atual['Length'].sum() < length_min) and (df_atual['Section'].iloc[-1] == dfs_separados[-1]['Section'].iloc[-1]):
            dfs_separados[-1] = pd.concat([dfs_separados[-1], df_atual], ignore_index=True)
        else:
            dfs_separados.append(df_atual)

    return dfs_separados


def SeparaMax (df_list, length_max):
    def SeparaIntersection(list_temp, length_max, intersection):
        # Verificando máximos de extensão e separando pela coluna "Intersection type"
        new_list_temp = []
        for sh in range(len(list_temp)):
            # Verifica se esta maior que o máximo
            if list_temp[sh]['Length'].sum() > length_max:
                df_atual = pd.DataFrame()
                for index, row in list_temp[sh].iterrows():
                    df_intersection = list_temp[sh].loc[[index]]
                    if df_intersection['Intersection type'].tolist()[0] == intersection:
                        df_atual = pd.concat([df_atual, list_temp[sh].loc[[index]]], ignore_index=True)
                        new_list_temp.append(df_atual)
                        df_atual = pd.DataFrame()
                    else:
                        df_atual = pd.concat([df_atual, list_temp[sh].loc[[index]]], ignore_index=True)
                if not df_atual.empty:
                    new_list_temp.append(df_atual)
            else:
                new_list_temp.append(list_temp[sh])
        return new_list_temp
    

    if checkvar.get() == True:
        # Ordem de prioridade para segmentação de rodovias
        intersection_order = (8, 7, 10, 4, 3, 17, 6, 9, 5, 2, 13, 1, 14, 15, 16)
        i = 0
        while i < len(intersection_order):
            df_new = SeparaIntersection(df_list, length_max, intersection_order[i])
            df_list = df_new
            i += 1
        return df_new
    
    else:
        return df_list


def Rename (new_df):
    sh_ini = 1
    df_final = pd.DataFrame()
    for item in new_df:
        for line in range(len(item)):
            item['Section'][line] = item['Section'][line] + ' - TH' + str(sh_ini)
        df_final = pd.concat([df_final, item], ignore_index=True)
        sh_ini = sh_ini + 1
    
    return df_final


def Button_func():
    entry = filedialog.askopenfilename()
    dir_entry.delete(0, tk.END)
    dir_entry.insert(0, entry)

    # Limpando tabelas
    for line in table_fim.get_children():
        table_fim.delete(line)
    for line in table_ini.get_children():
        table_ini.delete(line)
    
    # Lendo valores conforme tipo
    print(entry)
    if (entry.split(".")[1] == "xlsx") or (entry.split(".")[1] == "xls"):
        df_original = pd.read_excel(entry)
    elif entry.split(".")[1] == "csv":
        df_original = pd.read_csv(entry, delimiter=";")
    else:
        messagebox.showerror('Arquivo Invalido', 'Formatos aceitos .xlsx, .xls ou .csv')

    # Adicionando novos valores da tabela inicial
    cont = 0
    for col in df_original.columns.values:
        word = ""
        for leter in col:
            if leter == " ":
                word = word + "_"
            else:
                word = word + leter
        if cont in (5, 12, 62):
            table_fim.insert(parent="", index=tk.END, values=(cont, word))
        else:
            table_ini.insert(parent="", index=tk.END, values=(cont, word))
        cont = cont + 1


def item_delet_ini(_):
    for i in table_ini.selection():
        value = table_ini.item(i)['values']
        table_ini.delete(i)
        table_fim.insert(parent="", index=tk.END, values=value)


def item_delet_fim(_):
    for i in table_fim.selection():
        value = table_fim.item(i)['values']
        table_fim.delete(i)
        table_ini.insert(parent="", index=tk.END, values=value)


def up_item(_):
    for i in table_fim.selection():
        value = table_fim.item(i)['values']
        index = table_fim.index(i)
        table_fim.delete(i)
        table_fim.insert(parent="", index=index-1, values=value)


def down_item(_):
    for i in table_fim.selection():
        value = table_fim.item(i)['values']
        index = table_fim.index(i)
        table_fim.delete(i)
        table_fim.insert(parent="", index=index+1, values=value)


def Button_main():
    def Segmentation(df_original, length_min, length_max, segment_columns, path_final, csv):
        # Ajustando valores da input
        if csv:
            df_original['Length'] = df_original['Length'].str.replace(',','.').astype(float)
        # Iniciando segmentação
        df_list = SeparaDF(df_original, length_min, segment_columns)
        new_df = SeparaMax(df_list, length_max)
        df_final = Rename(new_df)
        df_final.to_csv(path_final, sep=";", index=False, encoding='utf-8-sig')
        messagebox.showinfo("Processo finalizado", "Os trechos homogêneos foram gerados e exportados!")

    # Caminho do arquivo
    path = dir_entry.get()
    path_final = path.split(".")[0] + "_segmentado.csv"

    try:
        length_max = float(spinbox2.get())
        length_min = float(spinbox1.get())
    except:
        messagebox.showinfo("Erro de entrada", "Insira valores numericos para a segmentação!")

    segment_columns = []
    for line in table_fim.get_children():
        temp = table_fim.item(line)['values'][1]
        segment_columns.append(temp.replace("_", " "))

    if len(segment_columns) == 0:
        messagebox.showerror("Erro!", 'Nenhuma Coluna Selecionada!')
    else:
        if (path.split(".")[1] == "xlsx") or (path.split(".")[1] == "xls"):
            df_original = pd.read_excel(path)
            Segmentation(df_original, length_min, length_max, segment_columns, path_final, False)
        elif path.split(".")[1] == "csv":
            df_original = pd.read_csv(path, delimiter=";", encoding='utf-8-sig')
            Segmentation(df_original, length_min, length_max, segment_columns, path_final, True)
        else:
            messagebox.showerror('Arquivo Invalido', 'Formatos aceitos .xlsx, .xls ou .csv')



# JANELA
root = tk.Tk()
root.resizable(False, False)
root.geometry("810x350")
language_var = tk.StringVar(value='pt')
root.title('Segmentação Homogênea - iRap')

# Selecionando diretório
dir_entry = ttk.Entry(root)
button = ttk.Button(root, text='Selecione o arquivo', command=lambda: Button_func())

button.place(x=10, y=10, width=130, height=25)
dir_entry.place(x=145, y=10, width=655, height=25)

# Cria tabelas
table_ini = ttk.Treeview(root, columns=['Ítem', 'Atributos'], show='headings')
table_ini.heading('Atributos', text='Atributos')
table_ini.heading('Ítem', text='Ítem')
table_ini.column("#1", width=40, anchor='center')
table_ini.column("#2", width=350, anchor='w')
table_ini.place(x=10, y=50)

table_fim = ttk.Treeview(root, columns=('Ítem', 'Atributos_Selecionados'), show='headings')
table_fim.heading('Atributos_Selecionados', text='Atributos_Selecionados')
table_fim.heading('Ítem', text='Ítem')
table_fim.column("#1", width=40, anchor='center')
table_fim.column("#2", width=350, anchor='w')
table_fim.place(x=410, y=50)

# Events
table_ini.bind('<Right>', item_delet_ini)
table_fim.bind('<Left>', item_delet_fim)
table_fim.bind('<Up>', up_item)
table_fim.bind('<Down>', down_item)

# Lable
label1 = ttk.Label(root, text='Segmento mínimo (km)')
label2 = ttk.Label(root, text='Segmento máximo (km)')

label1.place(x=10, y=290)
label2.place(x=150, y=290)

# Spinbox
spinbox1 = ttk.Spinbox(root, from_=0, to=1000)
spinbox2 = ttk.Spinbox(root, from_=0, to=1000)

spinbox1.place(x=10, y=310, width=130, height=25)
spinbox2.place(x=150, y=310, width=130, height=25)
spinbox1.insert(0, '1')
spinbox2.insert(0, '20')

# Check buttton
checkvar = tk.BooleanVar()
check1 = ttk.Checkbutton(root, text='Segmentar nas interseções?', variable=checkvar)
check1.place(x=290, y=310, width=200, height=25)

#Botão gerar
button_main = ttk.Button(root, text='Gerar Segmentação', command=lambda: Button_main())
button_main.place(x=470, y=310, width=130, height=25)

root.mainloop()

