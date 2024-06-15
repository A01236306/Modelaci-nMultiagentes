using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;

public class TCPIPServerAsync : MonoBehaviour
{
    private Socket listener;
    private List<Vector3> carPositions = new List<Vector3>();
    public GameObject[] prefabs;
    private CarDataList carDataList;
    private Dictionary<int, GameObject> instantiatedPrefabs = new Dictionary<int, GameObject>();
    private Dictionary<int, Vector3> previousPositions = new Dictionary<int, Vector3>();

    private async void Start()
    {
        Application.runInBackground = true;
        carDataList = new CarDataList();
        await StartListeningAsync();
    }

    private async Task StartListeningAsync()
    {
        listener = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        listener.Bind(new IPEndPoint(IPAddress.Parse("127.0.0.1"), 1102));
        listener.Listen(9999);

        while (true)
        {
            Debug.Log("Waiting for Connection");
            Socket handler = await listener.AcceptAsync();
            Debug.Log("Client Connected");

            byte[] sendBytes = Encoding.Default.GetBytes("I will send key");
            await handler.SendAsync(new ArraySegment<byte>(sendBytes), SocketFlags.None);

            await ReceiveDataAsync(handler);

            // Cerrar la conexión después de recibir los datos
            handler.Shutdown(SocketShutdown.Both);
            handler.Close();
        }
    }

    private async Task ReceiveDataAsync(Socket handler)
    {
        var buffer = new byte[8192];
        List<CarData> receivedData = new List<CarData>();

        while (true)
        {
            try
            {
                var received = await handler.ReceiveAsync(new ArraySegment<byte>(buffer), SocketFlags.None);

                if (received > 0)
                {
                    var data = Encoding.UTF8.GetString(buffer, 0, received).TrimEnd('$');
                    Debug.Log("Received from Client: " + data);

                    if (data == "")
                    {
                        break;
                    }

                    lock (carDataList)
                    {
                        receivedData.AddRange(JsonHelper.FromJson<List<CarData>>(data));
                        carPositions.Clear();
                    }
                }
                else
                {
                    // Si no se reciben datos, la conexión se ha cerrado desde el cliente
                    break;
                }
            }
            catch (SocketException ex) when (ex.SocketErrorCode == SocketError.ConnectionAborted)
            {
                Debug.LogWarning("La conexión se cerró abruptamente.");
                break;
            }
        }

        lock (carDataList)
        {
            carDataList.carData = receivedData;
        }

        foreach (var carData in carDataList.carData)
        {
            lock (carPositions)
            {
                Vector3 currentPosition = new Vector3(carData.pos[0], 0, carData.pos[1]);
                carPositions.Add(currentPosition);

                // Si el prefab ya fue instanciado, actualiza su posición y rotación
                if (instantiatedPrefabs.ContainsKey(carData.id))
                {
                    GameObject prefab = instantiatedPrefabs[carData.id];
                    prefab.transform.position = currentPosition;

                    // Calcula la dirección de movimiento y ajusta la rotación del prefab
                    Vector3 direction = currentPosition - previousPositions.GetValueOrDefault(carData.id, currentPosition);
                    float angle = Vector3.SignedAngle(Vector3.forward, direction, Vector3.up);
                    prefab.transform.rotation = Quaternion.Euler(0f, angle, 0f);

                    previousPositions[carData.id] = currentPosition;
                }
                else
                {
                    // Si no, instancia un nuevo prefab basado en el id del agente
                    int prefabIndex = carData.id % prefabs.Length;  // Asegura que el índice esté en el rango de prefabs
                    GameObject newPrefab = Instantiate(prefabs[prefabIndex], currentPosition, Quaternion.identity);
                    instantiatedPrefabs[carData.id] = newPrefab;
                    previousPositions[carData.id] = currentPosition;
                }
            }
        }
    }

    private void OnDisable()
    {
        listener?.Close();
    }

    private class JsonHelper
    {
        public static T FromJson<T>(string json)
        {
            Wrapper<T> wrapper = JsonUtility.FromJson<Wrapper<T>>("{\"data\":" + json + "}");
            return wrapper.data;
        }

        [Serializable]
        private class Wrapper<T>
        {
            public T data;
        }
    }

    [System.Serializable]
    public class CarData
    {
        public int id;
        public float[] pos;
    }

    [System.Serializable]
    public class CarDataList
    {
        public List<CarData> carData;
    }
}
