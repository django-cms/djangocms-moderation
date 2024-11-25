(function ($) {
    if (!$) {
        return;
    }

    $(function () {
      // INFO: it is not possible to put a form inside a form, so the moderation actions have to create their own form
      // on click.
        $(` .cms-moderation-action-btn,
            .js-moderation-action,
            .cms-actions-dropdown-menu-item-anchor`)
      .on('click', function (e) {
          e.preventDefault();

          // action currently being targeted
          let action = $(e.currentTarget);
          // get the form method being used?
          let formMethod = action.attr('class').indexOf('cms-form-get-method') === 1 ? 'POST' : 'GET';
          let csrfToken = formMethod === 'GET' ? '' : '<input type="hidden" name="csrfmiddlewaretoken" value="' +
            document.cookie.match(/csrftoken=([^;]*);?/)[1] + '">';
          let fakeForm = $(
            '<form style="display: none" action="' + action.attr('href') + '" method="' +
            formMethod + '">' + csrfToken +
            '</form>'
          );
          let body = window.top.document.body;
          let keepSideFrame = action.attr('class').indexOf('js-versioning-keep-sideframe') !== -1;

          // always break out of the sideframe, cause it was never meant to open cms views inside it
          try {
              if (!keepSideFrame) {
                  window.top.CMS.API.Sideframe.close();
              }
          } catch (err) { }
          if (keepSideFrame) {
              body = window.document.body;
          }

          fakeForm.appendTo(body).submit();
      });

        $('.js-versioning-close-sideframe').on('click', function () {
            try {
                window.top.CMS.API.Sideframe.close();
            } catch (e) { }
        });
    });

    // Hide django messages after timeout occurs to prevent content overlap
    $('document').ready(function () {
      // Targeting first item returned (there's only ever one messagelist per template):
        let messageList = document.getElementsByClassName('messagelist')[0];
        let interval = 20;
        let timeout = 500;

        if (messageList !== undefined) {
            for (let item of messageList.children) {
                item.style.opacity = 1;
                setTimeout(() => {
                    let fader = setInterval(() => {
                        item.style.opacity -= 0.05;
                        if (item.style.opacity < 0) {
                            item.style.display = 'none';
                            clearInterval(fader);
                        }

                    }, interval);
                }, timeout);
            }
        }
    });

    let closeBurgerMenu = function closeBurgerMenu() {
        $('.cms-actions-dropdown-menu').removeClass('open');
        $('.cms-actions-dropdown-menu').addClass('closed');
        $('.cms-moderation-action-btn').removeClass('open');
        $('.cms-moderation-action-btn').addClass('closed');
    };

    let toggleBurgerMenu = function toggleBurgerMenu(burgerMenuAnchor, optionsContainer) {
        let bm = $(burgerMenuAnchor);
        let op = $(optionsContainer);
        let closed = bm.hasClass('closed');

        closeBurgerMenu();

        if (closed) {
            bm.removeClass('closed').addClass('open');
            op.removeClass('closed').addClass('open');
        } else {
            bm.addClass('closed').removeClass('open');
            op.addClass('closed').removeClass('open');
        }

        let pos = bm.offset();
        let leftOffset = 200;

        op.css('left', pos.left - leftOffset);
        op.css('top', pos.top);
    };

    // Create burger menu:
    $(function () {
        let burger_menu_icon;

        if (typeof moderation_static_url_prefix === 'undefined') {
            burger_menu_icon = '/static/djangocms_moderation/svg/menu.svg';
        } else {
            // eslint-disable-next-line no-undef
            burger_menu_icon = `${moderation_static_url_prefix}svg/menu.svg`;
        }

        let createBurgerMenu = function createBurgerMenu(row) {

            let actions = $(row).children('.field-list_display_actions');

            if (!actions.length) {
              /* skip any rows without actions to avoid errors */
                return;
            }

            /* create burger menu anchor icon */
            let anchor = document.createElement('a');
            let icon = document.createElement('img');

            icon.setAttribute('src', burger_menu_icon);
            anchor.setAttribute('class', 'btn cms-moderation-action-btn closed');
            anchor.setAttribute('title', 'Actions');
            anchor.appendChild(icon);

            /* create options container */
            let optionsContainer = document.createElement('div');
            let ul = document.createElement('ul');

            /* 'cms-actions-dropdown-menu' class is the main selector for the menu,
            'cms-actions-dropdown-menu-arrow-right-top' keeps the menu arrow in position. */
            optionsContainer.setAttribute(
              'class',
              'cms-actions-dropdown-menu cms-actions-dropdown-menu-arrow-right-top');
            ul.setAttribute('class', 'cms-actions-dropdown-menu-inner');

            /* get the existing actions and move them into the options container */
            $(actions[0]).children('.cms-moderation-action-btn').each(function (index, item) {

                let li = document.createElement('li');
                /* create an anchor from the item */
                let li_anchor = document.createElement('a');
                const itemId = $(item).attr('id');
                const itemTarget = $(item).attr('target');
                const itemDataPopup = $(item).attr('data-popup');

                li_anchor.setAttribute('class', 'cms-actions-dropdown-menu-item-anchor');
                li_anchor.setAttribute('href', $(item).attr('href'));
                // Copy the id attribute if it is set
                if (itemId !== undefined) {
                    li_anchor.setAttribute('id', itemId);
                }
                // Copy the target attribute if it is set
                if (itemTarget !== undefined) {
                    li_anchor.setAttribute('target', itemTarget);
                }
                // Copy the data-popup attribute if it is set
                if (itemDataPopup !== undefined) {
                    li_anchor.setAttribute('data-popup', itemDataPopup);
                }

                if ($(item).hasClass('cms-form-get-method')) {
                    // Ensure the fake-form selector is propagated to the new anchor
                    li_anchor.classList.add('cms-form-get-method');
                }
                if ($(item).hasClass('related-widget-wrapper-link')) {
                    // Ensure we retain the class which defines whether an item opens in a modal
                    li_anchor.classList.add('related-widget-wrapper-link');
                }
                /* get the span which contains the img */
                let value = $(item).children('span')[0];

                /* move the icon image */
                li_anchor.appendChild($(value).children('img')[0]);

                /* create the button text and construct the button */
                let span = document.createElement('span');

                span.appendChild(
                  document.createTextNode(item.title)
                );

                li_anchor.appendChild(span);
                li.appendChild(li_anchor);
                ul.appendChild(li);

                /* destroy original replaced buttons */
                actions[0].removeChild(item);
            });

            /* add the options to the drop-down */
            optionsContainer.appendChild(ul);
            actions[0].appendChild(anchor);
            document.body.appendChild(optionsContainer);

            /* listen for burger menu clicks */
            anchor.addEventListener('click', function (ev) {
                ev.stopPropagation();
                toggleBurgerMenu(anchor, optionsContainer);
            });

            /* close burger menu if clicking outside */
            $(window).click(function () {
                closeBurgerMenu();
            });
        };

        $('#result_list').find('tr').each(function (index, item) {
            createBurgerMenu(item);
        });
    });
})((typeof django !== 'undefined' && django.jQuery) || (typeof CMS !== 'undefined' && CMS.$) || false);
