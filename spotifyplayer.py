import wavelink
from discord.ext import commands
from wavelink.ext import spotify

class SpotifyPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ps")
    async def play(self, ctx: commands.Context, *, search: str) -> None:
        if not ctx.voice_client:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = ctx.voice_client

        vc.autoplay = True

        decoded = spotify.decode_url(search)
        if not decoded or decoded['type'] not in (spotify.SpotifySearchType.track, spotify.SpotifySearchType.playlist):
            await ctx.send('Only music links and playlists are valid')
            return

        if decoded['type'] == spotify.SpotifySearchType.track:
            track: spotify.SpotifyTrack = await spotify.SpotifyTrack.search(decoded['id'])
            if not track:
                await ctx.send('This is not a valid URL from spotify.')
                return
                
            track = track[0] if type(track) == list else track
            if not vc.is_playing():
                await vc.play(track[0])
            else:
                await vc.queue.put_wait(track)

        elif decoded['type'] == spotify.SpotifySearchType.playlist:
            playlist_iterator = spotify.SpotifyTrack.iterator(query=decoded['id'], type=spotify.SpotifySearchType.playlist)
            playlist_tracks = []
            async for track in playlist_iterator:
                if 'album' in track.raw:
                    album = track.raw['album']
                    track.album = album['name'] if 'name' in album else None
                else:
                    track.album = None
                playlist_tracks.append(track)

            if not playlist_tracks:
                await ctx.send('This is not a valid URL from Spotify')
                return
            
            track = track[0] if type(track) == list else track
            for track in playlist_tracks:
                if not vc.is_playing():
                    await vc.play(track)
                else:
                    await vc.queue.put_wait(track)

async def setup(bot):
    await bot.add_cog(SpotifyPlayer(bot))