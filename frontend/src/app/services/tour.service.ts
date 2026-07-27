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
      element: '.board-panel',
      popover: {
        title: 'Ton échiquier',
        description:
          "Joue un coup en déplaçant une pièce. À chaque coup, l'assistant analyse " +
          'la nouvelle position et met à jour ses conseils, à droite.',
      },
    },
    {
      element: '[data-tour="verdict"]',
      popover: {
        title: 'Es-tu dans la théorie ?',
        description:
          "« Dans la théorie » signifie que ta position est connue et étudiée : des " +
          'milliers de joueurs sont déjà passés par là. « Hors théorie », tu sors des ' +
          "sentiers battus — ce n'est pas forcément mauvais, mais tu es livré à toi-même.",
      },
    },
    {
      element: '[data-tour="evaluation"]',
      popover: {
        title: 'Qui est mieux ?',
        description:
          "Un moteur d'échecs calcule qui a l'avantage. Un nombre positif favorise " +
          'les Blancs, négatif les Noirs. En dessous de 0,5 environ, la partie est ' +
          'équilibrée. L\'unité est le pion : +1,0 équivaut à un pion d\'avance.',
      },
    },
    {
      element: '[data-tour="moves"]',
      popover: {
        title: 'Ce que jouent les maîtres',
        description:
          'Les coups les plus fréquents dans les parties de haut niveau à partir de ' +
          'ta position, avec le nombre de parties où ils ont été joués. Plus le ' +
          "nombre est élevé, plus le coup est éprouvé.",
      },
    },
    {
      element: '[data-tour="context"]',
      popover: {
        title: "Comprendre l'ouverture",
        description:
          "Des explications rédigées sur l'ouverture que tu es en train de jouer : " +
          'son idée directrice, ses plans typiques. C\'est le « pourquoi » derrière les coups.',
      },
    },
    {
      element: '[data-tour="videos"]',
      popover: {
        title: 'Des vidéos pour aller plus loin',
        description:
          'Clique sur une vignette pour lancer la vidéo dans la page. Rien ne se ' +
          "charge tant que tu ne l'as pas demandé.",
      },
    },
    {
      element: '[data-tour="technical"]',
      popover: {
        title: 'Sous le capot',
        description:
          'Pour les curieux : la notation FEN de ta position et l\'état des services ' +
          "interrogés par l'assistant. Tu peux ignorer cette section sans problème.",
      },
    },
    {
      element: '[data-tour="replay"]',
      popover: {
        title: 'À toi de jouer',
        description:
          'Tu peux relancer cette visite à tout moment depuis ce bouton. Bonne partie !',
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
