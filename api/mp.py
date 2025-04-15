import mercadopago

sdk = mercadopago.SDK("TEST-475525b6-ad58-4631-a255-de10a0b318f3")

def criar_cobranca_pix(valor: float, nome: str, email: str):
    try:
        # Valores de fallback para segurança
        nome = nome.strip() if nome.strip() else "Usuário"
        email = email.strip() if email.strip() else "teste@teste.com"

        payment_data = {
            "transaction_amount": round(valor, 2),  # Garante float com duas casas
            "description": f"Depósito de {nome}",
            "payment_method_id": "pix",
            "payer": {
                "email": email,
                "first_name": nome,
                "identification": {
                    "type": "CPF",  # Pode ser obrigatório em alguns casos
                    "number": "12345678909"
                }
            },
            "notification_url": "https://seudominio.com/webhook",
            "binary_mode": True,
            "external_reference": f"deposito_{nome}_{valor}"
        }

        payment_response = sdk.payment().create(payment_data)

        if payment_response["status"] == 201:
            pagamento = payment_response["response"]
            if "point_of_interaction" in pagamento:
                return {
                    "qr_code": pagamento["point_of_interaction"]["transaction_data"]["qr_code"],
                    "qr_code_base64": pagamento["point_of_interaction"]["transaction_data"]["qr_code_base64"],
                    "id": pagamento["id"]
                }
            else:
                raise Exception(f"'point_of_interaction' ausente. Resposta: {pagamento}")
        else:
            raise Exception(f"Erro ao criar cobrança PIX. Detalhes: {payment_response}")

    except Exception as e:
        raise Exception(f"Erro ao criar cobrança no Mercado Pago: {str(e)}")
