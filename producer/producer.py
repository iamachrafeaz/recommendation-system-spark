import json
import time
import pandas as pd
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import NoBrokersAvailable


def init_kafka(retries=10, delay=5):
    admin_client = None
    for i in range(retries):
        try:
            # 1. Connexion Admin pour vérifier/créer le topic
            admin_client = KafkaAdminClient(bootstrap_servers=['broker:9092'])
            topic_name = 'product_reviews'
            if topic_name not in admin_client.list_topics():
                admin_client.create_topics([NewTopic(name=topic_name, num_partitions=1, replication_factor=1)])
                print(f"✅ Topic '{topic_name}' créé.")

            # 2. Initialisation du Producer
            producer = KafkaProducer(
                bootstrap_servers=['broker:9092'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                # On ajoute des retries internes au producer pour plus de sécurité
                retries=5
            )
            print("🚀 Connecté à Kafka avec succès !")
            return producer
        except NoBrokersAvailable:
            print(f"⏳ Kafka (broker) n'est pas encore prêt ({i + 1}/{retries})... pause {delay}s")
            time.sleep(delay)
        except Exception as e:
            print(f"⚠️ Erreur : {e}")
            time.sleep(delay)
        finally:
            if admin_client:
                admin_client.close()
    raise Exception("❌ Impossible de joindre Kafka.")


if __name__ == "__main__":
    producer = init_kafka()

    # Chargement des données
    df = pd.read_csv("reviews_10.csv")

    print(f"📦 Début de l'envoi de {len(df)} messages...")

    for _, row in df.iterrows():
        msg = {
            "user_id": str(row['UserId']),
            "product_id": str(row['ProductId']),
            "score": float(row['Score']),
            "time": int(row['Time'])  # Ton streaming utilise "time", pas "timestamp"
        }

        producer.send('product_reviews', msg)
        print(f"➡️ Envoyé : User {msg['user_id']} -> Product {msg['product_id']}")

        # On garde un petit sleep pour simuler un flux réel et ne pas saturer le dashboard
        time.sleep(1)

    producer.flush()
    print("🏁 Envoi terminé.")