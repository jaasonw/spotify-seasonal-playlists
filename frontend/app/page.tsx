import Image from "next/image";
import SpotifyWebApi from "spotify-web-api-node";

function createAuthUrl() {
  const scopes = [
    "user-read-private",
    "user-read-email",
    "playlist-read-private",
    "playlist-modify-private",
    "playlist-modify-public",
    "user-library-read",
    "user-library-modify",
  ];
  const spotifyApi = new SpotifyWebApi({
    redirectUri: process.env.redirect_uri,
    clientId: process.env.client_id,
  });
  return spotifyApi.createAuthorizeURL(scopes, "state", true);
}

export default function Home() {
  return (
    <>
      <section className="flex justify-center text-center py-8 mb-10 bg-slate-100">
        <div className="flex flex-col justify-center text-center">
          <h1 className="text-4xl font-medium">
            Spotify Seasonal Playlist Creator
          </h1>
          <p className="text-xl text-gray-500 my-3">
            Organize Your Liked Songs into Playlists for Every Season
          </p>
          <Image src="/banner.png" alt="preview" width={1092} height={315} />
          <p className="flex justify-center gap-2">
            <a
              href={createAuthUrl()}
              className="my-2 p-3 bg-blue-600 text-white rounded-md transition-all hover:bg-blue-700"
            >
              Try it here
            </a>
            <a
              className="my-2 p-3 bg-gray-500 text-white rounded-md transition-all hover:bg-gray-700"
              href="https://github.com/jaasonw/spotify-seasonal-playlists"
            >
              View the source
            </a>
          </p>
        </div>
      </section>
      <section className="flex flex-col justify-center text-center gap-5">
        <h1 className="text-4xl font-medium">How it works</h1>
        <div className="flex flex-row gap-10 items-center justify-center">
          <div className="flex flex-col items-center justify-center text-center p-2">
            <h3 className="text-3xl">Step 1: Link your Spotify account</h3>
            <p className="text-gray-500">
              Use the link above to give us the appropriate permissions
            </p>
            <Image src="/1.png" alt="step 1" width={380} height={404} />
          </div>
          <div className="flex flex-col items-center justify-center text-center p-2">
            <h3 className="text-3xl">Step 2: Like some songs</h3>
            <p className="text-gray-500">
              Every 10 minutes, we'll update your playlist with the songs you've
              liked
            </p>
            <Image src="/2.png" alt="step 2" width={380} height={404} />
          </div>
        </div>
      </section>
    </>
  );
}
