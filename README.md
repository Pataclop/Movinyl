<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/Pataclop/Movinyl">
    <img src="/logos/movinyl_logo_square_bold.png" alt="Logo" width="400">
  </a>

  <h3 align="center">Movinyl</h3>

  <p align="center">
    Capture the colors of your favorite movie!

  </p>
</p>



<!-- TABLE OF CONTENTS -->
## Table of Contents

* [About the Project](#about-the-project)
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
* [Usage](#usage)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)



<!-- ABOUT THE PROJECT -->
## About The Project

Movinyl is a fun visualization project to capture the colors and spirit of a movie through beautiful posters featuring the frames of a movie in a vibrant, vinyl-like disk.

Take a look at what we're talking about
 
![Example Result](https://github.com/Pataclop/Movinyl/blob/master/example_img/3.jpg)

<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

Everything required for the project is in the installation script within the repository.

### HOW TO CREATE A DISK


1. Compile & install some dependancies 
```sh
./0_SETUP
```
2. Put your movies in the PROCESSING_ZONE folder. WARNING : They will be deleted

3. Generate the disks (ressource intensive, go take a cup of wine)

```sh
./1_BATCH
```

### HOW TO CREATE A DISK - DOCKER 
(slower, but you can use your computer while it is processing)

1. Build the docker stuff


```sh
sudo docker build -t movinyl .
```
2. Generate the disks

```sh
docker run -v path-with-video-files:/app/PROCESSING_ZONE movinyl disk
```

### HOW TO CREATE A PAGE

Put the 4000x4000px images that you generated in the PAGE_ZONE folder. WARNING : They will be deleted. Expected format : title_year.png
```sh
./2_MAKE_PAGE
```

<!-- ROADMAP -->
## Roadmap

See the [open issues](https://github.com/Pataclop/Movinyl/issues) for a list of proposed features and known issues. Please feel free to add to our roadmap. 
* Multithreading for pages.cpp
* Reduce the number of scripts and instructions to make the experience more seamless
* QRcode in pages 
* opetions in page
* planche rework
* one script to do it all
* FASTER!

<!-- CONTRIBUTING -->
## Contributing

Any contributions you make are **greatly appreciated**. If you have any suggestions for our project or have coding experience and would like to join the project, please reach out to us at  project.movinyl@gmail.com!

Do not hesitate to add your disks to this album, or send us your creations by mail or weTransfer or other. (that would save us the time to re-process some movies, and discover some others).
Sharing is greatly appreciated. 
[google photo album](https://photos.app.goo.gl/TtnD8yMPEKirk46R6)
(4000x4000 pixels, PNG files)


For code contributions: 

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<!-- LICENSE -->
## License

MIT
<!-- CONTACT -->
## Contact

Please shoot us a message at: project.movinyl@gmail.com
Project Link: [https://github.com/Pataclop/Movinyl](https://github.com/Pataclop/Movinyl)


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/Pataclop/Movinyl.svg?style=flat-square
[contributors-url]: https://github.com/Pataclop/Movinyl/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Pataclop/Movinyl.svg?style=flat-square
[forks-url]: https://github.com/Pataclop/Movinyl/network/members
[stars-shield]: https://img.shields.io/github/stars/Pataclop/Movinyl.svg?style=flat-square
[stars-url]: https://github.com/Pataclop/Movinyl/stargazers
[issues-shield]: https://img.shields.io/github/issues/Pataclop/Movinyl.svg?style=flat-square
[issues-url]: https://github.com/Pataclop/Movinyl/issues
[license-shield]: https://img.shields.io/github/license/Pataclop/Movinyl.svg?style=flat-square
[license-url]: https://github.com/Pataclop/Movinyl/blob/master/LICENSE.txt
