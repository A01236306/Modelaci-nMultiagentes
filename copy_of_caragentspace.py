import agentpy as ap
import numpy as np
import socket
import json

# Función para enviar datos
import agentpy as ap
import numpy as np
import socket
import json

# Función para enviar datos
def send_data(data):
    host = '127.0.0.1'
    port = 1102

    try:
        # Dividir los datos en mensajes más pequeños
        max_message_size = 1024
        message_chunks = [data[i:i+max_message_size] for i in range(0, len(data), max_message_size)]

        for chunk in message_chunks:
            message = json.dumps(chunk) + "$"

            # Crear una nueva conexión para cada envío
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
                sock.sendall(message.encode('utf-8'))
                try:
                    response = sock.recv(1024).decode("utf-8")
                    print("Respuesta del servidor:", response)
                except ConnectionResetError:
                    print("La conexión se cerró abruptamente desde el lado del servidor.")
                    break  # Salir del bucle para evitar intentos adicionales

    except socket.error as e:
        print(f"Socket error: {e}")
    except Exception as e:
        print(f"Error sending data: {e}")

class Light(ap.Agent):
    def setup(self):
        self.state = 'green'
        self.pos = [0, 0]
        self.tag = 'V'

    def setup_pos_tag(self, pos, tag, state):
        self.tag = tag
        self.pos = pos
        self.state = state

    def change_state(self):
        if self.state == 'green':
            self.state = 'red'
        else:
            self.state = 'green'

class Car(ap.Agent):
    def setup(self):
        self.pos = [0, 0]
        self.velocity = [0, 0]
        self.objective = 'Forward'
        self.tag = 'V'

    def setup_pos(self, space, dir, tag, light):
        self.space = space
        self.pos = space.positions[self]
        self.velocity = [.2, 0] if self.pos[0] == 0 else [0, .2]
        self.objective = dir
        self.tag = tag
        self.light = light

    def update_position(self, space):
        if self.light.state == 'green':
            if self.tag == 'H':
                if self.objective == 'Right' and self.pos[0] >= (self.p.size)/2:
                    self.objective = 'Forward'
                    self.tag = 'V'
                    self.pos[0] = (self.p.size)/2
                    self.velocity[0] = 0
                    self.velocity[1] = 0.2
                else:
                    nList = [a for a in space.neighbors(self, 0.5).to_list() if (a.pos[0] > self.pos[0] and a.tag == self.tag)]
                    if len(nList) > 0:
                        self.velocity[0] = 0
                    else:
                        self.velocity[0] = 0.2
            elif self.tag == 'V':
                if self.objective == 'Right' and self.pos[1] >= (self.p.size)/2:
                    self.objective = 'Forward'
                    self.tag = 'H'
                    self.pos[1] = (self.p.size)/2
                    self.velocity[0] = 0.2
                    self.velocity[1] = 0
                else:
                    nList = [a for a in space.neighbors(self, 0.5).to_list() if (a.pos[1] > self.pos[1] and a.tag == self.tag)]
                    if len(nList) > 0:
                        self.velocity[1] = 0
                    else:
                        self.velocity[1] = 0.2
            self.pos = self.pos + self.velocity
            self.space.move_by(self, self.velocity)
        else:
            if self.tag == 'H':
                if (self.light.pos[0] - self.pos[0]) <= 1 and (self.light.pos[0] - self.pos[0]) >= 0.5:
                    self.velocity[0] = 0
                else:
                    nList = [a for a in space.neighbors(self, 0.5).to_list() if (a.pos[0] > self.pos[0] and a.tag == self.tag)]
                    if len(nList) > 0:
                        self.velocity[0] = 0
            else:
                if (self.light.pos[1] - self.pos[1]) <= 1 and (self.light.pos[1] - self.pos[1]) >= 0.5:
                    self.velocity[1] = 0
                else:
                    nList = [a for a in space.neighbors(self, 0.5).to_list() if (a.pos[1] > self.pos[1] and a.tag == self.tag)]
                    if len(nList) > 0:
                        self.velocity[1] = 0
            self.pos = self.pos + self.velocity
            self.space.move_by(self, self.velocity)

class CarModel(ap.Model):
    def setup(self):
        self.space = ap.Space(self, shape=(self.p.size, self.p.size))
        self.counter = 0

        lightPosH = [(self.p.size / 2) - 1, self.p.size / 2]
        lightPosV = [self.p.size / 2, (self.p.size / 2) - 1]

        self.lightH = Light(self)
        self.lightH.setup_pos_tag(lightPosH, 'H', 'green')

        self.lightV = Light(self)
        self.lightV.setup_pos_tag(lightPosV, 'V', 'red')

        self.space.add_agents([self.lightH, self.lightV])

    def step(self):
        if self.counter == 40:
            for light in self.space.agents:
                if isinstance(light, Light):
                    light.change_state()
            self.counter = 0

        if np.random.rand() < self.p.prob:
            r = self.p.size / 2
            pos = [np.array([0., r])] if np.random.rand() < .5 else [np.array([r, 0.])]
            dir = np.random.choice(['Forward', 'Right'])
            tag = 'H' if pos[0][0] == 0 else 'V'
            cars = ap.AgentList(self, 1, Car)
            self.space.add_agents(cars, positions=pos)
            cars.setup_pos(self.space, dir, tag, self.lightH if tag == 'H' else self.lightV)

        for car in self.space.agents:
            if isinstance(car, Car):
                car.update_position(self.space)

        remove = []
        for car in self.space.agents:
            if isinstance(car, Car) and (car.pos[0] < 0 or car.pos[0] >= self.p.size or car.pos[1] < 0 or car.pos[1] >= self.p.size):
                remove.append(car)

        self.space.remove_agents(remove)

        car_positions = [{'id': idx, 'pos': car.pos.tolist()} for idx, car in enumerate(self.space.agents) if isinstance(car, Car)]
        send_data(car_positions)

        self.counter += 1

parameters = {
    'size': 200,
    'street_width': 1,
    'steps': 2000,
    'seed': 123,
    'prob': .1
}

model = CarModel(parameters)
model.run()