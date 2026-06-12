(function ($) {
    if (!$) {
        return;
    }

    $(function () {
        let collection_sel = $('#id_collection');

        collection_sel.data('prev', collection_sel.val());
        collection_sel.on('change', function () {
            let jqThis = $(this);
            let newUrl;

            if (location.href.indexOf('collection_id') === -1) {
                newUrl = location.href + '&collection_id=' + jqThis.val();
            } else {
                newUrl = location.href.replace(
                    'collection_id=' + jqThis.data('prev'),
                    'collection_id=' + jqThis.val()
                );
            }
            location.href = newUrl;
        });
    });
})((typeof django !== 'undefined' && django.jQuery) || (typeof CMS !== 'undefined' && CMS.$) || false);
