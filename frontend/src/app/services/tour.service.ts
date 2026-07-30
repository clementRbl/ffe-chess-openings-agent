import { Injectable } from '@angular/core';
import { driver, type DriveStep } from 'driver.js';

// Clé de stockage local : le tour ne se déclenche automatiquement qu'au premier
// passage de l'utilisateur, mais reste rejouable à la demande.
const SEEN_KEY = 'ffe-tour-seen';

// Service pilotant la visite guidée de l'interface. Les étapes sont décrites
// ici plutôt que dans le composant afin de garder ce dernier centré sur
// l'échiquier et l'affichage des recommandations.
@Injectable({ providedIn: 'root' })
export class TourService {
  /** Étapes de la visite, dans l'ordre de lecture de l'interface. */
  private readonly steps: DriveStep[] = [
    {
      element: '.board-card',
      popover: {
        title: 'Votre échiquier',
        description:
          "Jouez un coup en déplaçant une pièce. À chaque coup, l'assistant analyse " +
          'la nouvelle position et met à jour ses conseils, à droite. La pastille ' +
          'sous le plateau rappelle à qui est le tour de jouer, et « Annuler » ' +
          'revient en arrière autant de fois que vous le souhaitez.',
      },
    },
    {
      element: '[data-tour="arrows"]',
      popover: {
        title: 'Les coups conseillés',
        description:
          'Les traits en pointillé partent de la pièce à déplacer et filent vers sa ' +
          'case d\'arrivée. Les pastilles vertes 1, 2 et 3 sont les coups les plus ' +
          'joués par les maîtres, dans cet ordre ; l\'étoile orange est le choix du ' +
          'moteur. Survolez un coup dans la liste de droite pour isoler sa flèche, ou ' +
          'coupez l\'affichage avec le bouton « Flèches ».',
      },
    },
    {
      element: '[data-tour="verdict"]',
      popover: {
        title: 'Êtes-vous dans la théorie ?',
        description:
          "« Dans la théorie » signifie que la position est connue et étudiée : des " +
          'milliers de joueurs sont déjà passés par là. « Hors théorie », vous sortez ' +
          "des sentiers battus — ce n'est pas forcément mauvais, mais vous êtes livré " +
          'à vous-même.',
      },
    },
    {
      element: '[data-tour="evaluation"]',
      popover: {
        title: 'Qui est mieux ?',
        description:
          "Le chiffre mesure l'écart entre les deux camps en pions : +1,00 veut dire " +
          "« les Blancs ont l'équivalent d'un pion de plus », −1,00 « les Noirs ». La " +
          'pastille à côté nomme le camp qui mène. La barre penche de son côté — les ' +
          'Blancs à gauche, les Noirs à droite. Tant que la frontière reste dans la ' +
          "bande claire du milieu, l'écart est trop petit pour départager qui que ce " +
          'soit : la position est équilibrée.',
      },
    },
    {
      element: '[data-tour="moves"]',
      popover: {
        title: 'Ce que jouent les maîtres',
        description:
          'Les coups les plus fréquents dans les parties de haut niveau à partir de ' +
          'cette position, avec le nombre de parties où ils ont été joués. Plus le ' +
          "nombre est élevé, plus le coup est éprouvé.",
      },
    },
    {
      element: '[data-tour="context"]',
      popover: {
        title: "Comprendre l'ouverture",
        description:
          "Des explications rédigées sur l'ouverture en cours de jeu : son idée " +
          'directrice, ses plans typiques. C\'est le « pourquoi » derrière les coups.',
      },
    },
    {
      element: '[data-tour="videos"]',
      popover: {
        title: 'Des vidéos pour aller plus loin',
        description:
          'Cliquez sur une vignette pour lancer la vidéo dans la page — rien ne se ' +
          "charge tant qu'elle n'a pas été demandée. Attention : ces vidéos " +
          "présentent l'ouverture dans son ensemble, elles ne commentent pas le " +
          'dernier coup joué.',
      },
    },
    {
      element: '[data-tour="technical"]',
      popover: {
        title: 'Sous le capot',
        description:
          'Pour les curieux : la notation FEN de la position et l\'état des services ' +
          "interrogés par l'assistant. Cette section peut être ignorée sans problème.",
      },
    },
    {
      element: '[data-tour="replay"]',
      popover: {
        title: 'À vous de jouer',
        description:
          'Cette visite peut être relancée à tout moment depuis ce bouton. Bonne partie !',
      },
    },
  ];

  /** Vrai si l'utilisateur n'a encore jamais vu la visite guidée. */
  get isFirstVisit(): boolean {
    try {
      return localStorage.getItem(SEEN_KEY) === null;
    } catch {
      // Navigation privée ou stockage désactivé : on ne bloque pas l'application.
      return false;
    }
  }

  /**
   * Lance la visite guidée.
   *
   * Les étapes dont l'élément est absent du DOM sont écartées : le panneau ne
   * contient pas toujours toutes les cartes (une position hors théorie n'a ni
   * contexte ni vidéos).
   */
  start(): void {
    const steps = this.steps.filter(
      (step) => !step.element || document.querySelector(step.element as string),
    );
    if (!steps.length) {
      return;
    }

    driver({
      steps,
      showProgress: true,
      progressText: 'Étape {{current}} sur {{total}}',
      nextBtnText: 'Suivant',
      prevBtnText: 'Précédent',
      doneBtnText: 'Terminer',
      onDestroyed: () => this.markAsSeen(),
    }).drive();
  }

  /** Mémorise que la visite a été vue, pour ne plus la déclencher seule. */
  private markAsSeen(): void {
    try {
      localStorage.setItem(SEEN_KEY, '1');
    } catch {
      // Stockage indisponible : la visite se reproposera au prochain passage.
    }
  }
}
