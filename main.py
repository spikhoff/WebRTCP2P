import asyncio
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from cryptography.fernet import Fernet


class P2PMessageClient:
    def __init__(self, signaling_url, key=None):
        self.signaling_url = signaling_url
        self.pc = RTCPeerConnection()
        self.channel = None
        self.key = key or Fernet.generate_key()
        self._setup_events()

    def _setup_events(self):
        self.pc.on("track", self._on_track)
        self.pc.on("icecandidate", self._on_ice_candidate)

    async def _on_track(self, track):
        # Handle incoming tracks (e.g., text messages)
        # You can decode the track data here based on your message format
        print(f"Received track: {track.kind}")

    async def _on_ice_candidate(self, candidate):
        if candidate:
            await self.send_signaling({"ice": candidate.to_json()})

    async def connect(self):
        # Implement signaling exchange using aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(self.signaling_url) as response:
                offer = RTCSessionDescription(sdp=await response.text())
                await self.pc.setLocalDescription(await self.pc.createOffer())
                await self.send_signaling({"sdp": self.pc.localDescription.sdp})
                await self.pc.setRemoteDescription(offer)  # Add await here

        self.channel = self.pc.createDataChannel("chat")
        self.channel.on("message", self._on_message)

    async def send_message(self, message):
        encrypted_message = self.key.encrypt(message.encode())
        await self.channel.send(encrypted_message)

    async def _on_message(self, message):
        decrypted_message = self.key.decrypt(message).decode()
        print(f"Received message: {decrypted_message}")

    async def send_signaling(self, data):
        # Implement sending data to the signaling server using aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(self.signaling_url, json=data) as response:
                # Handle potential errors and responses
                if response.status != 200:
                    print(f"Error sending signaling data: {response.status}")


async def main(signaling_url):
    client = P2PMessageClient(signaling_url)
    await client.connect()
    await client.send_message(b"Hello, world!")
    await asyncio.gather(client._on_message())  # Simulate listening for messages

if __name__ == "__main__":
    asyncio.run(main("your_signaling_url"))


# Unit tests (example using pytest)
async def test_message_encryption(client):
    message = b"Test message"
    encrypted = client.key.encrypt(message)
    decrypted = client.key.decrypt(encrypted).decode()
    assert message == decrypted

async def test_message_sending(client, mocker):
    mock_send = mocker.patch.object(client.channel, "send")
    await client.send_message(b"Test message")
    mock_send.assert_called_once_with(client.key.encrypt(b"Test message"))
