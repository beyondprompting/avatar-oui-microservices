import asyncio
import json
import sys
import argparse
import os
import requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# === Inicialización del servidor MCP ===
server = Server("support-it-mcp")

# === Constantes ===
PHONEBOOK_URL = os.getenv("PHONEBOOK_URL")

# === Carga el phonebook una sola vez ===
def load_phonebook() -> list[Dict[str, str]]:
    try:
        print("📥 Cargando phonebook...")
        response = requests.get(PHONEBOOK_URL)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        entries = []
        for entry in root.findall("DirectoryEntry"):
            name = entry.find("Name").text.strip()
            number = entry.find("Telephone").text.strip()
            entries.append({"name": name, "number": number})
        print(f"📒 Agenda cargada con {len(entries)} entradas.")
        return entries
    except Exception as e:
        print(f"❌ Error cargando la agenda: {e}")
        return []

PHONEBOOK_ENTRIES = load_phonebook()

# === Tools ===

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="agenda_telefonica",
            description="Busca un nombre por número interno o un número por nombre.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nombre de la persona a buscar (opcional)"
                    },
                    "number": {
                        "type": "string",
                        "description": "Número interno a buscar (opcional)"
                    }
                }
            }
        ),
        Tool(
            name="soporte_vpn",
            description="Proporciona ayuda para conectarse a la VPN de la empresa.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta relacionada con la conexión VPN (opcional)"
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "lookup_internal_number":
        result = handle_lookup_internal_number(
            name=arguments.get("name"),
            number=arguments.get("number")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
    
    elif name == "vpn_instructions":
        return [TextContent(type="text", text=VPN_RESPONSE)]

    else:
        return [TextContent(type="text", text=f"Herramienta desconocida: {name}")]

# === Implementación de herramientas ===

def handle_lookup_internal_number(name: Optional[str] = None, number: Optional[str] = None) -> Dict[str, Any]:
    print(f"📞 Tool llamada con: name={name}, number={number}")
    try:
        if name:
            name_lower = name.lower()
            matches = [
                entry for entry in PHONEBOOK_ENTRIES
                if name_lower in entry["name"].lower()
            ]
            if not matches:
                return {"success": False, "error": f'No se encontró ningún interno para el nombre "{name}".'}
            elif len(matches) == 1:
                entry = matches[0]
                return {
                    "success": True,
                    "result": f'El número interno de "{entry["name"]}" es {entry["number"]}.'
                }
            else:
                response = "Encontré varios resultados:\n\n"
                for entry in matches:
                    response += f'- {entry["name"]}: {entry["number"]}\n'
                return {
                    "success": True,
                    "result": response.strip()
                }

        elif number:
            for entry in PHONEBOOK_ENTRIES:
                if entry["number"] == number:
                    return {
                        "success": True,
                        "result": f'El número {number} pertenece a "{entry["name"]}".'
                    }
            return {"success": False, "error": f'No se encontró ningún nombre para el número "{number}".'}

        else:
            return {"success": False, "error": "Debes proporcionar un nombre o un número interno para buscar."}

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "debug_trace": traceback.format_exc()
        }


VPN_RESPONSE = """SOPORTE PARA CONEXIÓN VPN

Tu tarea principal también incluye guiar paso a paso a los usuarios para conectarse a la VPN de la empresa. Debés:

- Reconocer en qué paso está el usuario.
- Guiarlo en forma clara y precisa hacia el siguiente paso.
- Explicar cada paso con calma si lo piden.
- Responder consultas relacionadas con errores o dudas comunes.

---

**Pasos para la configuración del cliente:**

**Paso 1**  
Descargar e instalar cliente "FortiClient" según su sistema operativo: https://forticlient.com/downloads

**Paso 2**  
Seleccionar "Configure VPN"

**Paso 3**  
Seleccionar "IPsec VPN" y completar con los siguientes datos:
- Connection Name: Avatar BA  
- Description: Avatar Buenos Aires  
- Remote Gateway: 190.221.60.58  
- Authentication Method "Pre-shared key": <recibida por correo electrónico>  
- Presionar "Apply"

**Paso 4**  
Ejecutar el cliente Forticlient, seleccionar la conexión "Avatar BA" recién creada y acceder utilizando el usuario y contraseña de VPN recibido por correo.

---

**FAQ (Preguntas frecuentes)**

**¿Qué hago si no tengo usuario de VPN?**  
Tenés que enviar un correo a it@avatarla.con solicitando el acceso. Podés poner en copia a tu referente así el proceso de autorización es más rápido.

**¿Cómo accedo a los servidores una vez conectado a la VPN?**

*En Windows*  
Abrir el Explorador de Archivos:  
Presiona Win + E para abrir el Explorador de Archivos.  
Seleccionar "Conectar a unidad de red":  
Haz clic en "Este equipo" (o "Mi PC") en el panel izquierdo.  
Selecciona "Conectar a unidad de red".  
Elige una letra para la unidad: Z:, por ejemplo.  
En la carpeta, escribe \\192.168.3.3\[nombre_compartido].

*En Mac (OSx)*  
Presiona Cmd + K en el Finder.  
Escribe: smb://192.168.3.3/[nombre_compartido]  
Haz clic en "Conectar".  
Introduce usuario y contraseña si es necesario.

**Principales servidores disponibles:**  
- SRVFS1: \\192.168.3.6  
- SRVDC1: \\192.168.3.3  
- SRVDC2: \\192.168.3.31

**¿Si descargo archivos o miro YouTube conectado a la VPN uso el ancho de banda de la empresa?**  
Sí. Se recomienda desconectarse si no estás trabajando.
"""

# === Main ===

async def main():
    # Asegurar argumento `-f stdio` si no está presente
    if len(sys.argv) == 1:
        sys.argv.extend(["-f", "stdio"])

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True)
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔧 SERVIDOR MCP DE SOPORTE IT")
    print("Herramientas:")
    print("  - lookup_internal_number")
    print("  - vpn_instructions")
    print("=" * 60)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
