import { Component, OnInit } from '@angular/core';

import { AuthService } from '../../services/auth.service';
import { Client } from '../../models/client.interface';
import { FlashMessagesService } from 'angular2-flash-messages';

// import { Router } from '@angular/router';

@Component({
  selector: 'app-navbar',
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.scss']
})
export class NavbarComponent implements OnInit {

  isLoggedIn: boolean;
  loggedInUser: string;
  showRegister: boolean;
  constructor(
    // private router: Router,
    private flash: FlashMessagesService,
    private authSvc: AuthService
  ) { }

  ngOnInit(): void {
    this.authSvc.getAuth().subscribe(auth => {
      if (auth) {
        this.isLoggedIn = true;
        this.loggedInUser = auth.email;
      } else {
        this.isLoggedIn = false;
      }
    });
  }

  onLogoutClick(): void {
    this.authSvc.logout();
    this.flash.show('Logged out successfuly', {
      cssClass: 'alert-success',
      timeout: 4000
    });
    location.reload();
  }

}
